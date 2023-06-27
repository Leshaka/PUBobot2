import traceback
import re
from typing import Callable

from core.client import dc
from core.console import log
from core.utils import get_nick, parse_duration

import bot

from . import MessageContext

_commands = {}


def message_command(*aliases: str):

	def decorator(coro: Callable):
		for alias in aliases:
			_commands[alias] = coro

		async def wrapper(*args, **kwargs):
			return await coro(*args, **kwargs)
		return wrapper

	return decorator


@dc.event
async def on_message(message):
	if not message.content or message.content == "":
		return

	if (qc := bot.queue_channels.get(message.channel.id)) is None:
		return

	# special commands
	if re.match(r"^\+..", message.content):
		f, args = _commands.get('add'), [message.content[1:]]
	elif re.match(r"^-..", message.content):
		f, args = _commands.get('remove'), [message.content[1:]]
	elif message.content == "++":
		f, args = _commands.get('add'), []
	elif message.content == "--":
		f, args = _commands.get('remove'), []

	elif message.content[0] == qc.cfg.prefix:
		cmd_args = message.content[1:].split(' ', 1)
		f = _commands.get(cmd_args[0])
		args = cmd_args[1:]

	else:
		return

	if f is not None:
		ctx = MessageContext(qc, message)
		log.command("{} | #{} | {}: {}".format(
			ctx.channel.guild.name, ctx.channel.name, get_nick(message.author), message.content
		))

		if not bot.bot_ready:
			await ctx.error("Bot is under connection, please try agian later...", title="Error")
			return

		try:
			await f(ctx, *args)
		except bot.Exc.PubobotException as e:
			await ctx.error(str(e), title=e.__class__.__name__)
		except Exception as e:
			await ctx.error(str(e), title="RuntimeError")
			log.error("\n".join([
				f"Error processing a text message command.",
				f"QC: {ctx.channel.guild.name}>#{ctx.channel.name} ({qc.id}).",
				f"Member: {ctx.author} ({ctx.author.id}).",
				f"Content: `{message.content}`.",
				f"Exception: {str(e)}. Traceback:\n{traceback.format_exc()}=========="
			]))


@message_command('add', 'j')
async def _add(ctx: MessageContext, args: str = None):
	await bot.commands.add(ctx, queues=args)


@message_command('remove', 'l')
async def _remove(ctx: MessageContext, args: str = None):
	await bot.commands.remove(ctx, queues=args)


@message_command('who')
async def _remove(ctx: MessageContext, args: str = None):
	await bot.commands.who(ctx, queues=args)


@message_command('queues')
async def _queues(ctx: MessageContext, args: str = None):
	await bot.commands.show_queues(ctx)


@message_command('matches')
async def _matches(ctx: MessageContext, args: str = None):
	await bot.commands.show_matches(ctx)


@message_command('teams')
async def _teams(ctx: MessageContext, args: str = None):
	await bot.commands.show_teams(ctx)


@message_command('ready', 'r')
async def _ready(ctx: MessageContext, args: str = None):
	await bot.commands.set_ready(ctx, is_ready=True)


@message_command('notready', 'nr')
async def _not_ready(ctx: MessageContext, args: str = None):
	await bot.commands.set_ready(ctx, is_ready=False)


@message_command('subme')
async def _sub_me(ctx: MessageContext, args: str = None):
	await bot.commands.sub_me(ctx)


@message_command('subfor')
async def _sub_for(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}sub_for __@player__")
	elif (player := await ctx.get_member(args)) is None:
		raise bot.Exc.SyntaxError(ctx.qc.gt("Specified user not found."))

	await bot.commands.sub_for(ctx, player=player)


@message_command('capme')
async def _cap_me(ctx: MessageContext, args: str = None):
	await bot.commands.cap_me(ctx)


@message_command('capfor')
async def _cap_for(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}capfor __team__")

	await bot.commands.cap_for(ctx, team_name=args)


@message_command('pick', 'p')
async def _pick(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}pick __player__")

	members = [await ctx.get_member(i.strip()) for i in args.strip().split(" ")]
	if None in members:
		raise bot.Exc.SyntaxError(ctx.qc.gt("Specified user not found."))

	await bot.commands.pick(ctx, players=members)


@message_command('report_loss', 'rl')
async def _rl(ctx: MessageContext, args: str = None):
	await bot.commands.report(ctx, result='loss')


@message_command('report_draw', 'rd')
async def _rd(ctx: MessageContext, args: str = None):
	await bot.commands.report(ctx, result='draw')


@message_command('report_cancel', 'rc')
async def _rc(ctx: MessageContext, args: str = None):
	await bot.commands.report(ctx, result='abort')


@message_command('allow_offline', 'ao')
async def _ao(ctx: MessageContext, args: str = None):
	await bot.commands.allow_offline(ctx)


@message_command('expire')
async def _expire(ctx: MessageContext, args: str = None):
	duration = None
	if args:
		try:
			duration = parse_duration(args)
		except ValueError:
			raise bot.Exc.SyntaxError(ctx.qc.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))
	await bot.commands.expire(ctx, duration=duration)


@message_command('auto_ready', 'ar')
async def _auto_ready(ctx: MessageContext, args: str = None):
	duration = None
	if args:
		try:
			duration = parse_duration(args)
		except ValueError:
			raise bot.Exc.SyntaxError(ctx.qc.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))
	await bot.commands.auto_ready(ctx, duration=duration)


@message_command('rank')
async def _rank(ctx: MessageContext, args: str = None):
	if not args:
		await bot.commands.rank(ctx, player=None)
		return
	member = await ctx.get_member(args)
	await bot.commands.rank(ctx, player=member)


@message_command('leaderboard', 'lb')
async def _leaderboard(ctx: MessageContext, args: str = None):
	page = int(args) if args else None
	await bot.commands.leaderboard(ctx, page=page)


@message_command('lastgame', 'lg')
async def _lastgame(ctx: MessageContext, args: str = None):
	""" Guess parameter name on the supplied value type :peka5: """
	if not args:
		await bot.commands.last_game(ctx)
	elif args.isdigit():
		await bot.commands.last_game(ctx, match_id=int(args))
	elif (member := await ctx.get_member(args)) is not None:
		await bot.commands.last_game(ctx, player=member)
	else:
		await bot.commands.last_game(ctx, queue=args)


@message_command('cancel_match')
async def _cancel_match(ctx: MessageContext, args: str = None):
	if not args or not args.isdigit():
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}cancel_match __match_id__")
	await bot.commands.report_admin(ctx, match_id=int(args), abort=True)


@message_command('promote')
async def _promote(ctx: MessageContext, args: str = None):
	await bot.commands.promote(ctx, args)


@message_command('set_channel_cfg')
async def _set_qc_cfg(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}set_channel_cfg __json__")
	await bot.commands.set_qc_cfg(ctx, args.strip())


@message_command('set_queue_cfg')
async def _set_queue_cfg(ctx: MessageContext, args: str = ""):
	if len(args := args.split(" ", maxsplit=1)) != 2:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}set_queue_cfg __queue__ __json__")
	await bot.commands.set_queue_cfg(ctx, args[0], args[1].strip())


@message_command('stats_reset_player')
async def _stats_reset_player(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}stats_reset_player __@player__")

	await bot.commands.stats_reset_player(ctx, player=args)


@message_command('stats_replace_player')
async def _stats_replace_player(ctx: MessageContext, args: str = ""):
	if len(args := args.split(" ")) != 2:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}stats_replace_player __@player1__ __@player2__")

	await bot.commands.stats_replace_player(ctx, player1=args[0], player2=args[1])


@message_command('rating_hide_player')
async def _rating_hide(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}rating_hide __@player__")

	await bot.commands.rating_hide(ctx, player=args)


@message_command('rating_unhide_player')
async def _rating_unhide(ctx: MessageContext, args: str = None):
	if not args:
		raise bot.Exc.SyntaxError(f"Usage: {ctx.qc.cfg.prefix}rating_unhide_player __@player__")

	await bot.commands.rating_hide(ctx, player=args, hide=False)
