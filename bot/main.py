# -*- coding: utf-8 -*-
import traceback
from discord import ChannelType

from core.client import dc
from core.console import log
from core.config import cfg
from core.utils import error_embed, ok_embed

import bot

queue_channels = dict()  # {channel.id: QueueChannel()}
active_pickups = []
active_matches = []


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
		queue_channels.remove(qc)
		await message.channel.send(embed=ok_embed("The bot has been disabled."))
	else:
		await message.channel.send(embed=error_embed("The bot is not enabled on this channel."))


def update_qc_lang(qc_cfg):
	queue_channels[qc_cfg.p_key].update_lang()
