__all__ = ['auto_ready', 'expire', 'default_expire', 'allow_offline', 'switch_dms', 'cointoss', 'show_help', 'set_nick']

from time import time
from datetime import timedelta
from random import randint

from core.utils import seconds_to_str, find
from core.database import db
from core.config import cfg

import bot

MAX_EXPIRE_TIME = timedelta(hours=12)


async def auto_ready(ctx, duration: timedelta = None):
	if not duration:
		duration = timedelta(seconds=min([60*5, ctx.qc.cfg.max_auto_ready]))

	if duration.total_seconds() > ctx.qc.cfg.max_auto_ready:
		raise ctx.Exc.ValueError(ctx.qc.gt("Maximum auto_ready duration is {duration}.").format(
			duration=seconds_to_str(ctx.qc.cfg.max_auto_ready)
		))

	if ctx.author.id in bot.auto_ready.keys():
		bot.auto_ready.pop(ctx.author.id)
		await ctx.success(ctx.qc.gt("Your automatic ready confirmation is now turned off."))
		return

	bot.auto_ready[ctx.author.id] = int(time()) + duration.total_seconds()
	await ctx.success(
		ctx.qc.gt("During next {duration} your match participation will be confirmed automatically.").format(
			duration=duration.__str__()
		)
	)


async def expire(ctx, duration: timedelta = None):
	if not duration:
		if task := bot.expire.get(ctx.qc, ctx.author):
			await ctx.reply(ctx.qc.gt("You have {duration} expire time left.").format(
				duration=seconds_to_str(task.at - int(time()))
			))
			return
		await ctx.reply(ctx.qc.gt("You don't have an expire timer set right now."))
		return

	if duration > MAX_EXPIRE_TIME:
		raise bot.Exc.ValueError(ctx.qc.gt("Expire time must be less than {time}.".format(
			time=MAX_EXPIRE_TIME.__str__()
		)))

	bot.expire.set(ctx.qc, ctx.author, duration.total_seconds())
	await ctx.success(ctx.qc.gt("Set your expire time to {duration}.").format(
		duration=duration.__str__()
	))


async def default_expire(ctx, duration: timedelta = None, afk: bool = None, clear: bool = None):

	def _expire_to_reply(seconds):
		if seconds == 0:
			return ctx.qc.gt("You will be removed from queues on AFK status by default.")
		elif seconds is None:
			return ctx.qc.gt("Your expire time value will fallback to guild's settings.")
		else:
			return ctx.qc.gt("Your default expire time is {time}.".format(time=seconds_to_str(seconds)))

	if duration is None and afk is None and clear is None:
		data = await db.select_one(['expire'], 'players', where={'user_id': ctx.author.id})
		seconds = None if not data else data['expire']
		await ctx.reply(_expire_to_reply(seconds))
		return

	seconds = None
	if duration:
		if duration > MAX_EXPIRE_TIME:
			raise bot.Exc.ValueError(ctx.qc.gt("Expire time must be less than {time}.".format(
				time=MAX_EXPIRE_TIME.__str__()
			)))
		seconds = duration.total_seconds()
	if afk:
		seconds = 0

	try:
		await db.insert('players', {'user_id': ctx.author.id, 'expire': seconds})
	except db.errors.IntegrityError:
		await db.update('players', {'expire': seconds}, keys={'user_id': ctx.author.id})
	await ctx.success(_expire_to_reply(seconds))


async def allow_offline(ctx):
	if ctx.author.id in bot.allow_offline:
		bot.allow_offline.remove(ctx.author.id)
		await ctx.success(ctx.qc.gt("Your offline immunity is **off**."))
	else:
		bot.allow_offline.append(ctx.author.id)
		await ctx.success(ctx.qc.gt("Your offline immunity is **on** until the next match."))


async def switch_dms(ctx):
	data = await db.select_one(('allow_dm',), 'players', where={'user_id': ctx.author.id})
	if data:
		allow_dm = 1 if data['allow_dm'] == 0 else 0
		await db.update('players', {'allow_dm': allow_dm}, keys={'user_id': ctx.author.id})
	else:
		allow_dm = 0
		await db.insert('players', {'allow_dm': allow_dm, 'user_id': ctx.author.id})

	if allow_dm:
		await ctx.success(ctx.qc.gt("Your DM notifications is now turned on."))
	else:
		await ctx.success(ctx.qc.gt("Your DM notifications is now turned off."))


async def cointoss(ctx, side: str = None):
	pick = 0
	if side in ["tails", ctx.qc.gt("tails")]:
		pick = 1

	result = randint(0, 1)
	if pick == result:
		await ctx.reply(ctx.qc.gt("{member} won, its **{side}**!").format(
			member=ctx.author.mention, side=ctx.qc.gt(["heads", "tails"][result])
		))
	else:
		await ctx.reply(ctx.qc.gt("{member} lost, its **{side}**!").format(
			member=ctx.author.mention, side=ctx.qc.gt(["heads", "tails"][result])
		))


async def show_help(ctx, queue: str = None):
	if queue is None:
		if not ctx.qc.cfg.description:
			await ctx.reply_dm(cfg.HELP+"\nYou can edit this message with command `/channel set description`.")
		else:
			await ctx.reply_dm(ctx.qc.cfg.description)
		return
	if (q := find(lambda i: i.name.lower() == queue.lower(), ctx.qc.queues)) is None:
		raise bot.Exc.SyntaxError(f"Queue '{queue}' not found on the channel.")

	await ctx.reply_dm(q.cfg.description or ctx.qc.gt('Specified queue has no help answer set.'))


async def set_nick(ctx, nick: str):
	data = await db.select_one(
		['rating'], 'qc_players',
		where={'channel_id': ctx.author.id, 'user_id': ctx.author.id}
	)
	if not data or data['rating'] is None:
		rating = ctx.qc.rating.init_rp
	else:
		rating = data['rating']

	await ctx.author.edit(nick=f"[{rating}] " + nick)
	await ctx.ignore(ctx.qc.gt("Done."))
