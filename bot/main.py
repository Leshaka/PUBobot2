# -*- coding: utf-8 -*-
import traceback
import json

from core.console import log
from core.config import cfg
from core.utils import error_embed, ok_embed, get

import bot

queue_channels = dict()  # {channel.id: QueueChannel()}
active_queues = []
active_matches = []
waiting_reactions = dict()  # {message.id: function}
allow_offline = []  # [user_id]
last_match_id = None
auto_ready = dict()  # {user.id: timestamp}


async def enable_channel(message):
	if not (message.author.id == cfg.DC_OWNER_ID or message.channel.permissions_for(message.author).administrator):
		await message.channel.send(embed=error_embed(
			"One must posses the guild administrator permissions in order to use this command."
		))
		return
	if message.channel.id not in queue_channels.keys():
		queue_channels[message.channel.id] = await bot.QueueChannel.create(message.channel)
		await message.channel.send(embed=ok_embed("The bot has been enabled."))
	else:
		await message.channel.send(
			embed=error_embed("The bot is already enabled on this channel.")
		)


async def disable_channel(message):
	if not (message.author.id == cfg.DC_OWNER_ID or message.channel.permissions_for(message.author).administrator):
		await message.channel.send(embed=error_embed(
			"One must posses the guild administrator permissions in order to use this command."
		))
		return
	qc = queue_channels.get(message.channel.id)
	if qc:
		for queue in qc.queues:
			await queue.cfg.delete()
		await qc.cfg.delete()
		queue_channels.pop(message.channel.id)
		await message.channel.send(embed=ok_embed("The bot has been disabled."))
	else:
		await message.channel.send(embed=error_embed("The bot is not enabled on this channel."))


def update_qc_lang(qc_cfg):
	queue_channels[qc_cfg.p_key].update_lang()


def update_rating_system(qc_cfg):
	queue_channels[qc_cfg.p_key].update_rating_system()


def save_state():
	log.info("Saving state...")
	queues = []
	for qc in queue_channels.values():
		for q in qc.queues:
			if q.length > 0:
				queues.append(q.serialize())

	matches = []
	for match in active_matches:
		matches.append(match.serialize())

	f = open("saved_state.json", 'w')
	f.write(json.dumps(dict(queues=queues, matches=matches, allow_offline=bot.allow_offline, expire=bot.expire.serialize())))
	f.close()


async def load_state():
	try:
		with open("saved_state.json", "r") as f:
			data = json.loads(f.read())
	except IOError:
		return

	log.info("Loading state...")

	bot.allow_offline = list(data['allow_offline'])

	for qd in data['queues']:
		if qc := queue_channels.get(qd['channel_id']):
			if q := get(qc.queues, id=qd['queue_id']):
				await q.from_json(qd)
			else:
				log.error(f"Queue with id {qd['queue_id']} not found.")
		else:
			log.error(f"Queue channel with id {qd['channel_id']} not found.")

	for md in data['matches']:
		if qc := queue_channels.get(md['channel_id']):
			if q := get(qc.queues, id=md['queue_id']):
				await bot.Match.from_json(q, qc, md)
			else:
				log.error(f"Queue with id {md['queue_id']} not found.")
		else:
			log.error(f"Queue channel with id {md['channel_id']} not found.")

	if 'expire' in data.keys():
		await bot.expire.load_json(data['expire'])


async def remove_players(*users, reason=None):
	for qc in set((q.qc for q in active_queues)):
		await qc.remove_members(*users, reason=reason)


async def expire_auto_ready(frame_time):
	for user_id, at in list(auto_ready.items()):
		if at < frame_time:
			auto_ready.pop(user_id)
