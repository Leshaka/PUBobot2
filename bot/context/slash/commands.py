from typing import Callable
from nextcord import Interaction, SlashOption, Member, TextChannel
import traceback

from core.client import dc
from core.utils import error_embed, ok_embed, parse_duration
from core.console import log
from core.config import cfg

import bot


from . import SlashContext, autocomplete, groups


guild_kwargs = dict(guild_ids=cfg.DC_SLASH_SERVERS) if len(cfg.DC_SLASH_SERVERS) else dict()


def _parse_duration(ctx: SlashContext, s: str):
	try:
		return parse_duration(s)
	except ValueError:
		raise bot.Exc.SyntaxError(ctx.qc.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))


async def run_slash(coro: Callable, interaction: Interaction, **kwargs):
	if not bot.bot_ready:
		await interaction.response.send_message(
			embed=error_embed("Bot is under connection, please try agian later...", title="Error")
		)
		return
	qc = bot.queue_channels.get(interaction.channel_id)
	if qc is None:
		await interaction.response.send_message(embed=error_embed("Not in a queue channel.", title="Error"))
		return

	ctx = SlashContext(qc, interaction)
	try:
		await coro(ctx, **kwargs)
	except bot.Exc.PubobotException as e:
		await ctx.error(str(e), title=e.__class__.__name__)
	except Exception as e:
		await ctx.error(str(e), title="RuntimeError")
		log.error("\n".join([
			f"Error processing /slash command {coro.__name__}.",
			f"QC: {ctx.channel.guild.name}>#{ctx.channel.name} ({qc.id}).",
			f"Member: {ctx.author} ({ctx.author.id}).",
			f"Kwargs: {kwargs}.",
			f"Exception: {str(e)}. Traceback:\n{traceback.format_exc()}=========="
		]))


@groups.admin_queue.subcommand(name='create_pickup', description='Create new pickup queue.')
async def _create_pickup(
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
): await run_slash(bot.commands.create_pickup, interaction=interaction, name=name, size=size)


# queue -> ...

@groups.admin_queue.subcommand(name='list', description='List all queues on the channel.')
async def _show_queues(
	interaction: Interaction
): await run_slash(bot.commands.show_queues, interaction=interaction)


@groups.admin_queue.subcommand(name='show', description='Show a queue configuration.')
async def _cfg_queue(
		interaction: Interaction,
		queue: str
): await run_slash(bot.commands.cfg_queue, interaction=interaction, queue=queue)
_cfg_queue.on_autocomplete("queue")(autocomplete.queues)


@groups.admin_queue.subcommand(name='set', description='Configure a queue variable.')
async def _set_queue(
		interaction: Interaction,
		queue: str,
		variable: str,
		value: str
): await run_slash(bot.commands.set_queue, interaction=interaction, queue=queue, variable=variable, value=value)
_set_queue.on_autocomplete("queue")(autocomplete.queues)
_set_queue.on_autocomplete("variable")(autocomplete.queue_variables)


@groups.admin_queue.subcommand(name='delete', description='Delete a queue.')
async def _delete_queue(
	interaction: Interaction,
	queue: str = SlashOption(name="queue", description="Queue name.")
): await run_slash(bot.commands.delete_queue, interaction=interaction, queue=queue)
_delete_queue.on_autocomplete("queue")(autocomplete.queues)


@groups.admin_queue.subcommand(name='add_player', description='Add a player to a queue.')
async def _add_player(
	interaction: Interaction,
	player: Member = SlashOption(name="player", description="Member to add to the queue", verify=False),
	queue: str = SlashOption(name="queue", description="Queue to add to.")
): await run_slash(bot.commands.add_player, interaction=interaction, player=player, queue=queue)


@groups.admin_queue.subcommand(name='remove_player', description='Remove a player from queues.')
async def _remove_player(
	interaction: Interaction,
	player: Member = SlashOption(name="player", description="Member to remove from the queues", verify=False),
	queues: str = SlashOption(name="queues", description="Queues to remove the player from.", required=False)
): await run_slash(bot.commands.remove_player, interaction=interaction, player=player, queues=queues)


@groups.admin_queue.subcommand(name='clear', description='Remove players from the queues.')
async def _reset(
		interaction: Interaction,
		queue: str = SlashOption(name="queue", description="Only clear this queue.", required=False)
): await run_slash(bot.commands.reset, interaction=interaction, queue=queue)
_reset.on_autocomplete("queue")(autocomplete.queues)


@groups.admin_queue.subcommand(name='start', description='Start the queue.')
async def _start_queue(
	interaction: Interaction,
	queue: str
): await run_slash(bot.commands.start, interaction=interaction, queue=queue)
_start_queue.on_autocomplete("queue")(autocomplete.queues)


@groups.admin_queue.subcommand(name='split', description='Split the queue into N separate matches.')
async def _split_queue(
	interaction: Interaction,
	queue: str = SlashOption(),
	group_size: int = SlashOption(description="Amount of players per match", required=False),
	sort_by_rating: bool = SlashOption(description="Sort groups by players ratings", required=False)
): await run_slash(bot.commands.split, interaction=interaction, queue=queue, group_size=group_size, sort_by_rating=sort_by_rating)
_split_queue.on_autocomplete("queue")(autocomplete.queues)


# channel -> ...

@groups.admin_channel.subcommand(name='enable', description='Enable the bot on this channel.')
async def enable_channel(
		interaction: Interaction
):
	if not isinstance(interaction.channel, TextChannel):
		return await interaction.response.send_message(
			embed=error_embed('Must be used on a text channel.'), ephemeral=True
		)
	if not interaction.user.guild_permissions.administrator:
		return await interaction.response.send_message(
			embed=error_embed('You must possess server administrator permissions.'), ephemeral=True
		)
	if bot.queue_channels.get(interaction.channel_id) is not None:
		return await interaction.response.send_message(
			embed=error_embed('This channel is already enabled.'), ephemeral=True
		)

	await interaction.response.send_message(embed=ok_embed('The bot has been enabled.'))
	bot.queue_channels[interaction.channel.id] = await bot.QueueChannel.create(interaction.channel)


@groups.admin_channel.subcommand(name='disable', description='Disable the bot on this channel.')
async def disable_channel(
		interaction: Interaction
):
	if not interaction.user.guild_permissions.administrator:
		return await interaction.response.send_message(
			embed=error_embed('You must possess server administrator permissions.'), ephemeral=True
		)
	if (qc := bot.queue_channels.get(interaction.channel_id)) is None:
		return await interaction.response.send_message(
			embed=error_embed('This channel is not enabled.'), ephemeral=True
		)

	bot.queue_channels.pop(qc.id)
	await interaction.response.send_message(embed=ok_embed('The bot has been disabled.'))


@groups.admin_channel.subcommand(name='delete', description='Delete stats/configs and disable the bot on this channel.')
async def delete_channel(
		interaction: Interaction
):
	if not interaction.user.guild_permissions.administrator:
		return await interaction.response.send_message(
			embed=error_embed('You must possess server administrator permissions.'), ephemeral=True
		)
	if (qc := bot.queue_channels.get(interaction.channel_id)) is None:
		return await interaction.response.send_message(
			embed=error_embed('This channel is not enabled.'), ephemeral=True
		)

	for queue in qc.queues:
		await queue.cfg.delete()
	await qc.cfg.delete()
	bot.queue_channels.pop(qc.id)
	await interaction.response.send_message(embed=ok_embed('The bot has been disabled.'))


@groups.admin_channel.subcommand(name='show', description='List channel configuration.')
async def cfg_qc(
		interaction: Interaction
): await run_slash(bot.commands.cfg_qc, interaction=interaction)


@groups.admin_channel.subcommand(name='set', description='Configure a channel variable.')
async def _set_qc(
		interaction: Interaction,
		variable: str,
		value: str
): await run_slash(bot.commands.set_qc, interaction=interaction, variable=variable, value=value)
_set_qc.on_autocomplete("variable")(autocomplete.qc_variables)


# match -> ...

@groups.admin_match.subcommand(name='report', description='Report a match result as a moderator.')
async def _report_admin(
		interaction: Interaction,
		match_id: int,
		winner_team: str = SlashOption(required=False),
		draw: bool = SlashOption(required=False, default=False),
		abort: bool = SlashOption(required=False, default=False)
): await run_slash(
	bot.commands.report_admin, interaction=interaction, match_id=match_id, winner_team=winner_team, draw=draw, abort=abort
)
_report_admin.on_autocomplete('winner_team')(autocomplete.teams_by_match_id)
_report_admin.on_autocomplete('match_id')(autocomplete.match_ids)


@groups.admin_match.subcommand(name='create', description='Report a rating match manually.')
async def _report_manual(
		interaction: Interaction,
		queue: str,
		winners: str = SlashOption(description="List of won team players separated by space."),
		losers: str = SlashOption(description="List of lost team players separated by space."),
		draw: bool = SlashOption(required=False)
):
	async def _run(ctx, *args, _winners, _losers, **kwargs):
		_winners = [await ctx.get_member(i) for i in _winners.split(" ")]
		_losers = [await ctx.get_member(i) for i in _losers.split(" ")]
		if None in _winners or None in _losers:
			raise bot.Exc.ValueError("Failed to parse teams arguments.")
		await bot.commands.report_manual(ctx, *args, winners=_winners, losers=_losers, **kwargs)
	await run_slash(_run, interaction=interaction, queue=queue, _winners=winners, _losers=losers, draw=draw)


@groups.admin_match.subcommand(name='sub_player', description='Substitute a player in a match.')
async def _sub_force(
		interaction: Interaction,
		player1: Member = SlashOption(name="player1", description="The player to substitute for.", verify=False),
		player2: Member = SlashOption(name="player2", description="The player to substitute with.", verify=False)
): await run_slash(bot.commands.sub_force, interaction=interaction, player1=player1, player2=player2)


@groups.admin_match.subcommand(name='put', description='Put a player in a team.')
async def _put(
		interaction: Interaction,
		match_id: int,
		player: Member,
		team_name: str = SlashOption(name='team', description='Team name or unpicked')
): await run_slash(bot.commands.put, interaction=interaction, match_id=match_id, player=player, team_name=team_name)
_put.on_autocomplete('team_name')(autocomplete.teams_by_match_id)
_put.on_autocomplete('match_id')(autocomplete.match_ids)


# noadds -> ...

@groups.admin_noadds.subcommand(name='list', description='Show noadds list.')
async def _noadds(
		interaction: Interaction
): await run_slash(bot.commands.noadds, interaction=interaction)


@groups.admin_noadds.subcommand(name='add', description='Ban a player from participating in the queues.')
async def _noadd(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		duration: str = SlashOption(required=False),
		reason: str = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await bot.commands.noadd(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, player=player, _duration=duration, reason=reason)


@groups.admin_noadds.subcommand(name='remove', description='Remove a player from the noadds list.')
async def _forgive(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(bot.commands.forgive, interaction=interaction, player=player)


# phrases -> ...

@groups.admin_phrases.subcommand(name='add', description='Add a player phrase.')
async def _phrases_add(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		phrase: str = SlashOption()
): await run_slash(bot.commands.phrases_add, interaction=interaction, player=player, phrase=phrase)


@groups.admin_phrases.subcommand(name='clear', description='Clear player phrases.')
async def _phrases_clear(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
): await run_slash(bot.commands.phrases_clear, interaction=interaction, player=player)


# rating -> ...

@groups.admin_rating.subcommand(name='seed', description='Set player rating and deviation')
async def _rating_seed(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		rating: int = SlashOption(),
		deviation: int = SlashOption(required=False)
): await run_slash(bot.commands.rating_seed, interaction=interaction, player=player, rating=rating, deviation=deviation)


@groups.admin_rating.subcommand(name='penality', description='Subtract points from player rating.')
async def _rating_penality(
		interaction: Interaction,
		player: Member = SlashOption(verify=False),
		points: int = SlashOption(),
		reason: str = SlashOption(required=False)
): await run_slash(bot.commands.rating_penality, interaction=interaction, player=player, penality=points, reason=reason)


@groups.admin_rating.subcommand(name='hide_player', description='Hide player from the leaderboard.')
async def _rating_hide(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(bot.commands.rating_hide, interaction=interaction, player=player, hide=True)


@groups.admin_rating.subcommand(name='reset', description='Reset rating data on the channel.')
async def _rating_reset(
		interaction: Interaction
): await run_slash(bot.commands.rating_reset, interaction=interaction)


@groups.admin_rating.subcommand(name='snap', description='Snap players ratings to rank values.')
async def _rating_snap(
		interaction: Interaction
): await run_slash(bot.commands.rating_snap, interaction=interaction)


# stats -> ...

@groups.admin_stats.subcommand(name='show', description='Show channel or player stats.')
async def _stats(
		interaction: Interaction,
		player: Member = SlashOption(required=False, verify=False),
): await run_slash(bot.commands.stats, interaction=interaction, player=player)


@groups.admin_stats.subcommand(name='reset', description='Reset all stats data on the channel.')
async def _stats_reset(
		interaction: Interaction
): await run_slash(bot.commands.stats_reset, interaction=interaction)


@groups.admin_stats.subcommand(name='reset_player', description='Reset player stats.')
async def _stats_reset_player(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(bot.commands.stats_reset_player, interaction=interaction, player=player)


@groups.admin_stats.subcommand(name='stats_replace_player', description='Replace player1 with player2.')
async def _stats_replace_player(
		interaction: Interaction,
		player1: Member = SlashOption(verify=False),
		player2: Member = SlashOption(verify=False)
): await run_slash(bot.commands.stats_replace_player, interaction=interaction, player1=player1, player2=player2)


@groups.admin_stats.subcommand(name='undo_match', description='Undo a finished match.')
async def _stats_undo_match(
		interaction: Interaction,
		match_id: int
): await run_slash(bot.commands.undo_match, interaction=interaction, match_id=match_id)


# root commands

@dc.slash_command(name='add', description='Add yourself to the channel queues.', **guild_kwargs)
async def _add(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Queues you want to add to.",
		required=False)
): await run_slash(bot.commands.add, interaction=interaction, queues=queues)
_add.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='remove', description='Remove yourself from the channel queues.', **guild_kwargs)
async def _remove(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Queues you want to add to.",
		required=False)
): await run_slash(bot.commands.remove, interaction=interaction, queues=queues)
_remove.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='who', description='List added players.', **guild_kwargs)
async def _who(
	interaction: Interaction,
	queues: str = SlashOption(
		name="queues",
		description="Specify queues to list.",
		required=False)
): await run_slash(bot.commands.who, interaction=interaction, queues=queues)
_who.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='promote', description='Promote a queue.', **guild_kwargs)
async def promote(
		interaction: Interaction,
		queue: str = SlashOption(required=False)
): await run_slash(bot.commands.promote, interaction=interaction, queue=queue)
promote.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='subscribe', description='Subscribe to a queue promotion role.', **guild_kwargs)
async def subscribe(
		interaction: Interaction,
		queues: str
): await run_slash(bot.commands.subscribe, interaction=interaction, queues=queues, unsub=False)
subscribe.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='unsubscribe', description='Unsubscribe from a queue promotion role.', **guild_kwargs)
async def unsubscribe(
		interaction: Interaction,
		queues: str
): await run_slash(bot.commands.subscribe, interaction=interaction, queues=queues, unsub=True)
unsubscribe.on_autocomplete("queues")(autocomplete.queues)


@dc.slash_command(name='server', description='Show queue server.', **guild_kwargs)
async def server(
		interaction: Interaction,
		queue: str
): await run_slash(bot.commands.server, interaction=interaction, queue=queue)
server.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='maps', description='List a queue maps.', **guild_kwargs)
async def maps(
		interaction: Interaction,
		queue: str
): await run_slash(bot.commands.maps, interaction=interaction, queue=queue, one=False)
maps.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='map', description='Print a random map.', **guild_kwargs)
async def _map(
		interaction: Interaction,
		queue: str
): await run_slash(bot.commands.maps, interaction=interaction, queue=queue, one=True)
_map.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='matches', description='Show active matches on the channel.', **guild_kwargs)
async def _matches(
		interaction: Interaction
): await run_slash(bot.commands.show_matches, interaction=interaction)


@dc.slash_command(name='teams', description='Show teams on your current match.', **guild_kwargs)
async def _teams(
		interaction: Interaction
): await run_slash(bot.commands.show_teams, interaction=interaction)


@dc.slash_command(name='ready', description='Confirm participation during the check-in stage.', **guild_kwargs)
async def _ready(
		interaction: Interaction
): await run_slash(bot.commands.set_ready, interaction=interaction, is_ready=True)


@dc.slash_command(name='notready', description='Abort participation during the check-in stage.', **guild_kwargs)
async def _not_ready(
		interaction: Interaction
): await run_slash(bot.commands.set_ready, interaction=interaction, is_ready=False)


@dc.slash_command(name='subme', description='Request a substitute', **guild_kwargs)
async def _sub_me(
		interaction: Interaction
): await run_slash(bot.commands.sub_me, interaction=interaction)


@dc.slash_command(name='subfor', description='Become a substitute', **guild_kwargs)
async def _sub_for(
		interaction: Interaction,
		player: Member = SlashOption(name="player", description="The player to substitute for.", verify=False)
): await run_slash(bot.commands.sub_for, interaction=interaction, player=player)


@dc.slash_command(name='capfor', description='Become a captain', **guild_kwargs)
async def _cap_for(
		interaction: Interaction,
		team: str
): await run_slash(bot.commands.cap_for, interaction=interaction, team_name=team)
_cap_for.on_autocomplete('team')(autocomplete.teams_by_author)


# TODO: make possible to pick multiple players within singe command
@dc.slash_command(name='pick', description='Pick a player.', **guild_kwargs)
async def _pick(
		interaction: Interaction,
		player: Member = SlashOption(name="player", verify=False),
): await run_slash(bot.commands.pick, interaction=interaction, players=[player])


@dc.slash_command(name='report', description='Report match result.', **guild_kwargs)
async def _report(
		interaction: Interaction,
		result: str = SlashOption(choices=['loss', 'draw', 'abort'])
): await run_slash(bot.commands.report, interaction=interaction, result=result)


@dc.slash_command(name='lastgame', description='Show last game details.', **guild_kwargs)
async def _last_game(
		interaction: Interaction,
		queue: str = SlashOption(required=False),
		player: Member = SlashOption(required=False, verify=False),
		match_id: int = SlashOption(required=False)
): await run_slash(bot.commands.last_game, interaction=interaction, queue=queue, player=player, match_id=match_id)
_last_game.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='top', description='Show top players on the channel.', **guild_kwargs)
async def _top(
		interaction: Interaction,
		period: str = SlashOption(required=False, choices=['day', 'week', 'month', 'year']),
): await run_slash(bot.commands.top, interaction=interaction, period=period)


@dc.slash_command(name='rank', description='Show rating profile.', **guild_kwargs)
async def _rank(
		interaction: Interaction,
		player: Member = SlashOption(required=False, verify=False),
): await run_slash(bot.commands.rank, interaction=interaction, player=player)


@dc.slash_command(name='leaderboard', description='Show rating leaderboard.', **guild_kwargs)
async def _leaderboard(
		interaction: Interaction,
		page: int = SlashOption(required=False),
): await run_slash(bot.commands.leaderboard, interaction=interaction, page=page)


@groups.admin_rating.subcommand(name='unhide_player', description='Unhide player from the leaderboard.')
async def _rating_unhide(
		interaction: Interaction,
		player: Member = SlashOption(verify=False)
): await run_slash(bot.commands.rating_hide, interaction=interaction, player=player, hide=False)


@dc.slash_command(name='auto_ready', description='Confirm next match check-in automatically.', **guild_kwargs)
async def _auto_ready(
		interaction: Interaction,
		duration: str = SlashOption(required=False),
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await bot.commands.auto_ready(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration)


@dc.slash_command(name='expire', description='Set or show your current expire timer.', **guild_kwargs)
async def _expire(
		interaction: Interaction,
		duration: str = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await bot.commands.expire(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration)


@dc.slash_command(name='expire_default', description='Set or show your default expire timer.', **guild_kwargs)
async def _default_expire(
		interaction: Interaction,
		duration: str = SlashOption(required=False),
		afk: bool = SlashOption(required=False),
		clear: bool = SlashOption(required=False)
):
	async def _run(ctx, *args, _duration=None, **kwargs):
		if _duration:
			_duration = _parse_duration(ctx, _duration)
		await bot.commands.default_expire(ctx, *args, duration=_duration, **kwargs)

	await run_slash(_run, interaction=interaction, _duration=duration, afk=afk, clear=clear)


@dc.slash_command(name='allow_offline', description='Switch your offline status immunity.', **guild_kwargs)
async def _allow_offline(
		interaction: Interaction,
): await run_slash(bot.commands.allow_offline, interaction=interaction)


@dc.slash_command(name='switch_dms', description='Toggles DMs on queue start.', **guild_kwargs)
async def _switch_dms(
		interaction: Interaction,
): await run_slash(bot.commands.switch_dms, interaction=interaction)


@dc.slash_command(name='cointoss', description='Toss a coin.', **guild_kwargs)
async def _cointoss(
		interaction: Interaction,
		side: str = SlashOption(choices=['heads', 'tails'], required=False)
): await run_slash(bot.commands.cointoss, interaction=interaction, side=side)


@dc.slash_command(name='help', description='Show channel or queue help.', **guild_kwargs)
async def _help(
		interaction: Interaction,
		queue: str = SlashOption(name="queue", required=False)
): await run_slash(bot.commands.show_help, interaction=interaction, queue=queue)
_help.on_autocomplete("queue")(autocomplete.queues)


@dc.slash_command(name='commands', description='Show commands list.', **guild_kwargs)
async def _commands(
		interaction: Interaction,
): await interaction.response.send_message(cfg.COMMANDS_URL, ephemeral=True)


@dc.slash_command(name='nick', description='Change your nickname with the rating prefix.', **guild_kwargs)
async def _nick(
		interaction: Interaction,
		nick: str
): await run_slash(bot.commands.set_nick, interaction=interaction, nick=nick)

