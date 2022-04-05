from typing import Callable
from nextcord import Interaction, SlashOption, Member
import traceback

from core.client import dc
from core.utils import error_embed, parse_duration
from core.console import log

from bot import queue_channels, Exc
from bot import commands

from . import SlashContext, autocomplete

GUILD_ID = 745999774649679923


def _parse_duration(ctx: SlashContext, s: str):
	try:
		return parse_duration(s)
	except ValueError:
		raise Exc.SyntaxError(ctx.qc.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))


async def run_slash(coro: Callable, interaction: Interaction, **kwargs):
	qc = queue_channels.get(interaction.channel_id)
	if qc is None:
		await interaction.response.send_message(embed=error_embed("Not in a queue channel.", title="Error"))
		return

	ctx = SlashContext(qc, interaction)
	try:
		await coro(ctx, **kwargs)
	except Exc.PubobotException as e:
		await ctx.error(str(e), title=e.__class__.__name__)
	except Exception as e:
		await ctx.error(str(e), title="RuntimeError")
		log.error("\n".join([
			f"Error processing /slash command {coro.__name__}.",
			f"QC: {ctx.channel.guild.name}>#{ctx.channel.name} ({qc.id}).",
			f"Member: {ctx.author} ({ctx.author.id}).",
			f"Kwargs: {kwargs}.",
			f"{str(e)}. Traceback:\n{traceback.format_exc()}=========="
		]))


@dc.slash_command(name='add', description='Add yourself to the channel queues.', guild_ids=[GUILD_ID])
async def add(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Queues you want to add to.",
		required=False)
): await run_slash(commands.add, interaction=interaction, queues=queues)
add.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='remove', description='Remove yourself from the channel queues.', guild_ids=[GUILD_ID])
async def remove(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Queues you want to add to.",
		required=False)
): await run_slash(commands.remove, interaction=interaction, queues=queues)
remove.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='who', description='List added players.', guild_ids=[GUILD_ID])
async def who(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Specify queues to list.",
		required=False)
): await run_slash(commands.who, interaction=interaction, queues=queues)
who.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='create_pickup', description='Create new pickup queue.', guild_ids=[GUILD_ID])
async def create_pickup(
	interaction: Interaction,
	name: str = SlashOption(
		name="name",
		description="Queue name."),
	size: int = SlashOption(
		name="size",
		description="Queue size.",
		required=False,
		default=8
	)
): await run_slash(commands.create_pickup, interaction=interaction, name=name, size=size)


@dc.slash_command(name='delete_queue', description='Delete a queue.', guild_ids=[GUILD_ID])
async def delete_queue(
	interaction: Interaction,
	queue: str = SlashOption(name="queue", description="Queue name.")
): await run_slash(commands.delete_queue, interaction=interaction, queue=queue)
delete_queue.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='queues', description='List all queues on the channel.', guild_ids=[GUILD_ID])
async def show_queues(
	interaction: Interaction
): await run_slash(commands.show_queues, interaction=interaction)


@dc.slash_command(name='add_player', description='Add a player to a queue.', guild_ids=[GUILD_ID])
async def add_player(
	interaction: Interaction,
	player: Member = SlashOption(name="player", description="Member to add to the queue", verify=False),
	queue: str = SlashOption(name="queue", description="Queue to add to.")
): await run_slash(commands.add_player, interaction=interaction, player=player, queue=queue)


@dc.slash_command(name='remove_player', description='Add a player to a queue.', guild_ids=[GUILD_ID])
async def remove_player(
	interaction: Interaction,
	player: Member = SlashOption(name="player", description="Member to remove from the queues", verify=False),
	queues: str = SlashOption(name="queues", description="Queues to remove the player from.", required=False)
): await run_slash(commands.add_player, interaction=interaction, player=player, queue=queues)


@dc.slash_command(name='set', description='Configure a channel variable.', guild_ids=[GUILD_ID])
async def set_qc(
		interaction: Interaction,
		variable: str,
		value: str
): await run_slash(commands.set_qc, interaction=interaction, variable=variable, value=value)
set_qc.on_autocomplete("variable")(autocomplete.qc_variables)


@dc.slash_command(name='set_queue', description='Configure a queue variable.', guild_ids=[GUILD_ID])
async def set_queue(
		interaction: Interaction,
		queue: str,
		variable: str,
		value: str
): await run_slash(commands.set_queue, interaction=interaction, queue=queue, variable=variable, value=value)
set_queue.on_autocomplete("queue")(autocomplete.queues)
set_queue.on_autocomplete("variable")(autocomplete.queue_variables)


@dc.slash_command(name='cfg', description='List channel configuration.', guild_ids=[GUILD_ID])
async def cfg_qc(
		interaction: Interaction
): await run_slash(commands.cfg_qc, interaction=interaction)


@dc.slash_command(name='cfg_queue', description='Configure a queue variable.', guild_ids=[GUILD_ID])
async def cfg_queue(
		interaction: Interaction,
		queue: str
): await run_slash(commands.cfg_queue, interaction=interaction, queue=queue)
cfg_queue.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='promote', description='Promote a queue.', guild_ids=[GUILD_ID])
async def promote(
		interaction: Interaction,
		queue: str
): await run_slash(commands.promote, interaction=interaction, queue=queue)
promote.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='reset', description='Reset channel queues.', guild_ids=[GUILD_ID])
async def reset(
		interaction: Interaction,
		queue: str = SlashOption(name="queue", description="Only reset this queue.", required=False)
): await run_slash(commands.reset, interaction=interaction, queue=queue)
reset.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='subscribe', description='Subscribe to a queue promotion role.', guild_ids=[GUILD_ID])
async def subscribe(
		interaction: Interaction,
		queues: str
): await run_slash(commands.subscribe, interaction=interaction, queues=queues, unsub=False)
subscribe.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='unsubscribe', description='Unsubscribe from a queue promotion role.', guild_ids=[GUILD_ID])
async def unsubscribe(
		interaction: Interaction,
		queues: str
): await run_slash(commands.subscribe, interaction=interaction, queues=queues, unsub=True)
unsubscribe.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='server', description='Show queue server.', guild_ids=[GUILD_ID])
async def server(
		interaction: Interaction,
		queue: str
): await run_slash(commands.server, interaction=interaction, queue=queue)
server.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='maps', description='List a queue maps.', guild_ids=[GUILD_ID])
async def maps(
		interaction: Interaction,
		queue: str
): await run_slash(commands.maps, interaction=interaction, queue=queue, one=False)
maps.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='map', description='Print a random map.', guild_ids=[GUILD_ID])
async def _map(
		interaction: Interaction,
		queue: str
): await run_slash(commands.maps, interaction=interaction, queue=queue, one=True)
_map.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='matches', description='Show active matches on the channel.', guild_ids=[GUILD_ID])
async def _matches(
		interaction: Interaction
): await run_slash(commands.show_matches, interaction=interaction)


@dc.slash_command(name='teams', description='Show teams on your current match.', guild_ids=[GUILD_ID])
async def _teams(
		interaction: Interaction
): await run_slash(commands.show_teams, interaction=interaction)


@dc.slash_command(name='ready', description='Confirm participation during the check-in stage.', guild_ids=[GUILD_ID])
async def _ready(
		interaction: Interaction
): await run_slash(commands.set_ready, interaction=interaction, is_ready=True)


@dc.slash_command(name='notready', description='Abort participation during the check-in stage.', guild_ids=[GUILD_ID])
async def _not_ready(
		interaction: Interaction
): await run_slash(commands.set_ready, interaction=interaction, is_ready=False)


@dc.slash_command(name='subme', description='Request a substitute', guild_ids=[GUILD_ID])
async def _sub_me(
		interaction: Interaction
): await run_slash(commands.sub_me, interaction=interaction)


@dc.slash_command(name='subfor', description='Become a substitute', guild_ids=[GUILD_ID])
async def _sub_for(
		interaction: Interaction,
		player: Member = SlashOption(name="player", description="The player to substitute for.", verify=False)
): await run_slash(commands.sub_for, interaction=interaction, player=player)


@dc.slash_command(name='subforce', description='Substitute a player in a match.', guild_ids=[GUILD_ID])
async def _sub_force(
		interaction: Interaction,
		player1: Member = SlashOption(name="player1", description="The player to substitute for.", verify=False),
		player2: Member = SlashOption(name="player2", description="The player to substitute with.", verify=False)
): await run_slash(commands.sub_force, interaction=interaction, player1=player1, player2=player2)


@dc.slash_command(name='capfor', description='Become a captain', guild_ids=[GUILD_ID])
async def _cap_for(
		interaction: Interaction,
		team: str
): await run_slash(commands.cap_for, interaction=interaction, team_name=team)


# TODO: make possible to pick multiple players within singe command
@dc.slash_command(name='pick', description='Pick a player.', guild_ids=[GUILD_ID])
async def _pick(
		interaction: Interaction,
		player: Member = SlashOption(name="player", verify=False),
): await run_slash(commands.pick, interaction=interaction, players=[player])


@dc.slash_command(name='report_admin', description='Report a match result as a moderator.', guild_ids=[GUILD_ID])
async def _report_admin(
		interaction: Interaction,
		match_id: int,
		winner_team: str = SlashOption(required=False),
		draw: bool = SlashOption(required=False, default=False),
		abort: bool = SlashOption(required=False, default=False)
): await run_slash(
	commands.report_admin, interaction=interaction, match_id=match_id, winner_team=winner_team, draw=draw, abort=abort
)


@dc.slash_command(name='report', description='Report match result.', guild_ids=[GUILD_ID])
async def _report(
		interaction: Interaction,
		result: str = SlashOption(choices=['loss', 'draw', 'abort'])
): await run_slash(commands.report, interaction=interaction, result=result)


@dc.slash_command(name='lastgame', description='Show last game details.', guild_ids=[GUILD_ID])
async def _last_game(
		interaction: Interaction,
		queue: str = SlashOption(required=False),
		player: Member = SlashOption(required=False, verify=False),
		match_id: int = SlashOption(required=False)
): await run_slash(commands.last_game, interaction=interaction, queue=queue, player=player, match_id=match_id)
_last_game.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='stats', description='Show channel or player stats.', guild_ids=[GUILD_ID])
async def _stats(
		interaction: Interaction,
		player: Member = SlashOption(required=False, verify=False),
): await run_slash(commands.stats, interaction=interaction, player=player)


@dc.slash_command(name='top', description='Show top players on the channel.', guild_ids=[GUILD_ID])
async def _top(
		interaction: Interaction,
		period: str = SlashOption(required=False, choices=['day', 'week', 'month', 'year']),
): await run_slash(commands.top, interaction=interaction, period=period)


@dc.slash_command(name='rank', description='Show rating profile.', guild_ids=[GUILD_ID])
async def _rank(
		interaction: Interaction,
		player: Member = SlashOption(required=False, verify=False),
): await run_slash(commands.rank, interaction=interaction, player=player)


@dc.slash_command(name='leaderboard', description='Show rating leaderboard.', guild_ids=[GUILD_ID])
async def _leaderboard(
		interaction: Interaction,
		page: int = SlashOption(required=False),
): await run_slash(commands.leaderboard, interaction=interaction, page=page)


@dc.slash_command(name='noadds', description='Show noadds list.', guild_ids=[GUILD_ID])
async def _noadds(
		interaction: Interaction
): await run_slash(commands.noadds, interaction=interaction)


@dc.slash_command(name='noadd', description='Ban a player from participating in the queues.', guild_ids=[GUILD_ID])
async def _noadd(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		duration: str = SlashOption(required=False),
		reason: str = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await commands.noadd(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, player=player, _duration=duration, reason=reason)


@dc.slash_command(name='forgive', description='Remove a player from the noadds list.', guild_ids=[GUILD_ID])
async def _forgive(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(commands.forgive, interaction=interaction, player=player)


@dc.slash_command(name='rating_seed', description='Set player rating and deviation', guild_ids=[GUILD_ID])
async def _rating_seed(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		rating: int = SlashOption(),
		deviation: int = SlashOption(required=False)
): await run_slash(commands.rating_seed, interaction=interaction, player=player, rating=rating, deviation=deviation)


@dc.slash_command(name='rating_penality', description='Subtract points from player rating.', guild_ids=[GUILD_ID])
async def _rating_penality(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		points: int = SlashOption(),
		reason: str = SlashOption(required=False)
): await run_slash(commands.rating_penality, interaction=interaction, player=player, penality=points, reason=reason)


@dc.slash_command(name='rating_hide', description='Hide player from the leaderboard.', guild_ids=[GUILD_ID])
async def _rating_hide(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(commands.rating_hide, interaction=interaction, player=player, hide=True)


@dc.slash_command(name='rating_unhide', description='Unhide player from the leaderboard.', guild_ids=[GUILD_ID])
async def _rating_hide(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(commands.rating_hide, interaction=interaction, player=player, hide=False)


@dc.slash_command(name='rating_reset', description='Reset rating data on the channel.', guild_ids=[GUILD_ID])
async def _rating_reset(
		interaction: Interaction
): await run_slash(commands.rating_reset, interaction=interaction)


@dc.slash_command(name='rating_snap', description='Snap players ratings to rank values.', guild_ids=[GUILD_ID])
async def _rating_snap(
		interaction: Interaction
): await run_slash(commands.rating_snap, interaction=interaction)


@dc.slash_command(name='stats_reset', description='Reset all stats data on the channel.', guild_ids=[GUILD_ID])
async def _stats_reset(
		interaction: Interaction
): await run_slash(commands.stats_reset, interaction=interaction)


@dc.slash_command(name='stats_reset_player', description='Reset player stats.', guild_ids=[GUILD_ID])
async def _stats_reset_player(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(commands.stats_reset_player, interaction=interaction, player=player)


@dc.slash_command(name='stats_replace_player', description='Replace player1 with player2.', guild_ids=[GUILD_ID])
async def _stats_replace_player(
		interaction: Interaction,
		player1: Member = SlashOption(verify=False),
		player2: Member = SlashOption(verify=False)
): await run_slash(commands.stats_replace_player, interaction=interaction, player1=player1, player2=player2)


@dc.slash_command(name='phrases_add', description='Add a player phrase.', guild_ids=[GUILD_ID])
async def _phrases_add(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		phrase: str = SlashOption()
): await run_slash(commands.phrases_add, interaction=interaction, player=player, phrase=phrase)


@dc.slash_command(name='phrases_clear', description='Clear player phrases.', guild_ids=[GUILD_ID])
async def _phrases_add(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
): await run_slash(commands.phrases_clear, interaction=interaction, player=player)


@dc.slash_command(name='auto_ready', description='Confirm next match check-in automatically.', guild_ids=[GUILD_ID])
async def _auto_ready(
		interaction: Interaction,
		duration: str = SlashOption(required=False),
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await commands.auto_ready(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration)


@dc.slash_command(name='expire', description='Set or show your current expire timer.', guild_ids=[GUILD_ID])
async def _expire(
		interaction: Interaction,
		duration: str = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await commands.expire(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration)


@dc.slash_command(name='expire_default', description='Set or show your default expire timer.', guild_ids=[GUILD_ID])
async def _default_expire(
		interaction: Interaction,
		duration: str = SlashOption(required=False),
		afk: bool = SlashOption(required=False),
		clear: bool = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await commands.default_expire(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration, afk=afk, clear=clear)


@dc.slash_command(name='allow_offline', description='Switch your offline status immunity.', guild_ids=[GUILD_ID])
async def _allow_offline(
		interaction: Interaction,
): await run_slash(commands.allow_offline, interaction=interaction)


@dc.slash_command(name='switch_dms', description='Toggles DMs on queue start.', guild_ids=[GUILD_ID])
async def _switch_dms(
		interaction: Interaction,
): await run_slash(commands.switch_dms, interaction=interaction)


@dc.slash_command(name='cointoss', description='Toss a coin.', guild_ids=[GUILD_ID])
async def _cointoss(
		interaction: Interaction,
		side: str = SlashOption(choices=['heads', 'tails'], required=False)
): await run_slash(commands.cointoss, interaction=interaction, side=side)


@dc.slash_command(name='help', description='Show channel or queue help.', guild_ids=[GUILD_ID])
async def _help(
		interaction: Interaction,
		queue: str = SlashOption(name="queue", required=False)
): await run_slash(commands.show_help, interaction=interaction, queue=queue)
reset.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='nick', description='Change your nickname with the rating prefix.', guild_ids=[GUILD_ID])
async def _nick(
		interaction: Interaction,
		nick: str
): await run_slash(commands.set_nick, interaction=interaction, nick=nick)
