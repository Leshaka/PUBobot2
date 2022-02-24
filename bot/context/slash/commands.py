from typing import Callable
from nextcord import Interaction, SlashOption, Member
import traceback

from core.client import dc
from core.utils import error_embed
from core.console import log

from bot import queue_channels, Exc
from bot import commands

from . import SlashContext, autocomplete

GUILD_ID = 745999774649679923


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
		log.error(f"Error processing last /slash command. Traceback:\n{traceback.format_exc()}======")


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
cfg_queue.on_autocomplete("queue")(autocomplete.queues)
