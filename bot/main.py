# -*- coding: utf-8 -*-
import traceback
import json
from discord import ChannelType

from core.client import dc
from core.console import log
from core.config import cfg
from core.utils import error_embed, ok_embed, get

import bot

queue_channels = dict()  # {channel.id: QueueChannel()}
active_pickups = []
active_matches = []
waiting_reactions = dict()  # {message.id: function}


@dc.event
async def on_think(frame_time):
	for match in active_matches:
		await match.think(frame_time)
	await bot.expire.think(frame_time)


@dc.event
async def on_message(message):
	log.chat('{}: {}'.format(message.author, message.content))

	if message.channel.type != ChannelType.text:  # This is a private message
		return

	if message.content == '!enable_pubobot':
		await enable_channel(message)
	elif message.content == '!disable_pubobot':
		await disable_channel(message)

	qc = queue_channels.get(message.channel.id)
	if qc:
		await qc.process_msg(message)


@dc.event
async def on_reaction_add(reaction, user):
	if user.id != dc.user.id and reaction.message.id in waiting_reactions.keys():
		await waiting_reactions[reaction.message.id](reaction, user)


@dc.event
async def on_reaction_remove(reaction, user):  # FIXME: this event does not get triggered for some reason
	if user.id != dc.user.id and reaction.message.channel.id in waiting_reactions.keys():
		await waiting_reactions[reaction.message.id](reaction, user, remove=True)


@dc.event
async def on_ready():
	log.info(f"Logged in discord as '{dc.user.name}#{dc.user.discriminator}'.")
	log.info("Loading queue channels...")
	for channel_id in await bot.QueueChannel.cfg_factory.p_keys():
		channel = dc.get_channel(channel_id)
		if channel:
			queue_channels[channel_id] = await bot.QueueChannel.create(channel)
			log.info(f"\tInit channel {channel.guild.name}>#{channel.name} successful.")
		else:
			log.info(f"\tCould not reach a text channel with id {channel_id}.")

	await load_state()
	log.info("Done.")


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
		queue_channels.pop(message.channel.id)
		await message.channel.send(embed=ok_embed("The bot has been disabled."))
	else:
		await message.channel.send(embed=error_embed("The bot is not enabled on this channel."))


def update_qc_lang(qc_cfg):
	queue_channels[qc_cfg.p_key].update_lang()


def update_rating_system(qc_cfg):
	queue_channels[qc_cfg.p_key].update_rating_system()


def remove_members(*user_ids, reason=None):
	for qc in queue_channels.values():
		qc.remove_members()


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
	f.write(json.dumps(dict(queues=queues, matches=matches)))
	f.close()


async def load_state():
	try:
		with open("saved_state.json", "r") as f:
			data = json.loads(f.read())
	except IOError:
		return

	log.info("Loading state...")

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
