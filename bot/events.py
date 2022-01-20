from discord import ChannelType, Activity, ActivityType

from core.client import dc
from core.console import log
from core.config import cfg
import bot


@dc.event
async def on_think(frame_time):
	for match in bot.active_matches:
		await match.think(frame_time)
	await bot.expire.think(frame_time)
	await bot.noadds.think(frame_time)
	await bot.stats.jobs.think(frame_time)
	await bot.expire_auto_ready(frame_time)


@dc.event
async def on_message(message):
	if message.channel.type == ChannelType.private and message.author.id != dc.user.id:
		await message.channel.send(cfg.HELP)

	if message.channel.type != ChannelType.text:
		return

	if message.content == '!enable_pubobot':
		await bot.enable_channel(message)
	elif message.content == '!disable_pubobot':
		await bot.disable_channel(message)

	qc = bot.queue_channels.get(message.channel.id)
	if qc:
		await qc.process_msg(message)


@dc.event
async def on_reaction_add(reaction, user):
	if user.id != dc.user.id and reaction.message.id in bot.waiting_reactions.keys():
		await bot.waiting_reactions[reaction.message.id](reaction, user)


@dc.event
async def on_reaction_remove(reaction, user):  # FIXME: this event does not get triggered for some reason
	if user.id != dc.user.id and reaction.message.channel.id in bot.waiting_reactions.keys():
		await bot.waiting_reactions[reaction.message.id](reaction, user, remove=True)


@dc.event
async def on_ready():
	await dc.change_presence(activity=Activity(type=ActivityType.watching, name=cfg.STATUS))
	if not dc.was_ready:  # Connected for the first time, load everything
		dc.was_ready = True
		bot.last_match_id = await bot.stats.last_match_id()
		log.info(f"Logged in discord as '{dc.user.name}#{dc.user.discriminator}'.")
		log.info("Loading queue channels...")
		for channel_id in await bot.QueueChannel.cfg_factory.p_keys():
			channel = dc.get_channel(channel_id)
			if channel:
				bot.queue_channels[channel_id] = await bot.QueueChannel.create(channel)
				await bot.queue_channels[channel_id].update_info()
				log.info(f"\tInit channel {channel.guild.name}>#{channel.name} successful.")
			else:
				log.info(f"\tCould not reach a text channel with id {channel_id}.")

		await bot.load_state()
	else:  # Reconnected, fetch new channel objects
		log.info("Reconnected to discord.")
		for qc in list(bot.queue_channels.values()):
			if channel := dc.get_channel(qc.id) is not None:
				qc.channel = channel
			else:
				bot.queue_channels.pop(qc.id)
				log.error("ERROR! Channel missing after reconnect {}>#{} ({})!".format(
					qc.cfg.cfg_info.get('guild_name'), qc.cfg.cfg_info.get('channel_name'), qc.id
				))

	log.info("Done.")


@dc.event
async def on_member_update(before, after):
	if str(after.status) in ['idle', 'offline']:
		if after.id not in bot.allow_offline:
			for qc in filter(lambda i: i.channel and i.channel.guild.id == after.guild.id, bot.queue_channels.values()):
				await qc.auto_remove(after)


@dc.event
async def on_member_remove(member):
	for qc in filter(lambda i: i.channel and i.channel.guild.id == member.guild.id, bot.queue_channels.values()):
		await qc.remove_members(member, reason="left guild")
