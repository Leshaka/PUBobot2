from discord import ChannelType

from core.client import dc
from core.console import log
import bot


@dc.event
async def on_think(frame_time):
	for match in bot.active_matches:
		await match.think(frame_time)
	await bot.expire.think(frame_time)


@dc.event
async def on_message(message):
	log.chat('{}: {}'.format(message.author, message.content))

	if message.channel.type != ChannelType.text:  # This is a private message
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
	bot.last_match_id = await bot.stats.last_match_id()
	log.info(f"Logged in discord as '{dc.user.name}#{dc.user.discriminator}'.")
	log.info("Loading queue channels...")
	for channel_id in await bot.QueueChannel.cfg_factory.p_keys():
		channel = dc.get_channel(channel_id)
		if channel:
			bot.queue_channels[channel_id] = await bot.QueueChannel.create(channel)
			log.info(f"\tInit channel {channel.guild.name}>#{channel.name} successful.")
		else:
			log.info(f"\tCould not reach a text channel with id {channel_id}.")

	await bot.load_state()
	log.info("Done.")


@dc.event
async def on_member_update(before, after):
	if str(after.status) in ['idle', 'offline']:
		if after.id not in bot.allow_offline:
			for qc in filter(lambda i: i.channel.guild.id == after.guild.id, bot.queue_channels.values()):
				await qc.auto_remove(after)


@dc.event
async def on_member_remove(member):
	for qc in filter(lambda i: i.channel.guild.id == member.guild.id, bot.queue_channels.values()):
		await qc.remove_members(member, reason="left guild")
