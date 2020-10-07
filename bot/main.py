# -*- coding: utf-8 -*-
import traceback
from discord import ChannelType

from core.client import dc
from core.console import log


@dc.event
async def on_message(message):
	log.chat('{}: {}'.format(message.author, message.content))

	if message.channel.type != ChannelType.text:  # This is a private message
		return

	if message.content == '!hello':
		await message.channel.send('Hello world!')
