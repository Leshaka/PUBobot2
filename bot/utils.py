from asyncio import sleep as asleep
from asyncio import create_task
from nextcord import DiscordException

from bot import queue_channels
from core.client import dc
from core.console import log


async def _leave_empty_guilds():
	""" Leave all guilds which does not have any QueueChannels """
	used_ids = set((qc.channel.guild.id for qc in queue_channels.values()))
	used_ids.add(110373943822540800)  # Discord bots guild
	for guild in dc.guilds:
		if guild.id not in used_ids:
			log.info(f"...Leaving empty guild '{guild.name}' ({guild.id})...")
			try:
				await guild.leave()
			except DiscordException as e:
				log.error(f"Failed leaving empty guild: {str(e)}.")
			await asleep(1)


async def leave_empty_guilds():
	""" Make it run in the background """
	create_task(_leave_empty_guilds())


async def _notice(text):
	""" Send a text notification to all QueueChannels """
	for qc in queue_channels.values():
		log.info(f"...Sending notice to {qc.channel.guild.name}>{qc.channel.name}...")
		try:
			await qc.channel.send(text)
		except DiscordException as e:
			log.error(f"Could not send message to channel {qc.channel.guild.name}>{qc.channel.name}: {str(e)}")
		await asleep(1)


async def notice(*args, **kwargs):
	create_task(_notice(*args, **kwargs))
