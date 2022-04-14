from typing import List
from nextcord import Interaction

from core.utils import find, get

from bot import QueueChannel, queue_channels, active_matches


async def queues(interaction: Interaction, queue: str) -> List[str]:
	if (qc := queue_channels.get(interaction.channel_id)) is not None:
		return [q.name for q in qc.queues if q.name.startswith(queue)]
	else:
		return []


async def qc_variables(interaction: Interaction, variable: str) -> List[str]:
	return sorted([v for v in QueueChannel.cfg_factory.variables.keys() if v.startswith(variable)])[:10]


async def queue_variables(interaction: Interaction, variable: str) -> List[str]:
	if (qc := queue_channels.get(interaction.channel_id)) is None:
		return []
	interaction_queue = find(lambda i: i['name'] == 'queue', interaction.data['options'][0]['options'])
	if interaction_queue and (queue := get(qc.queues, name=interaction_queue['value'])):
		return sorted([v for v in queue.cfg_factory.variables.keys() if v.startswith(variable)])[:10]
	return []


async def match_ids(interaction: Interaction, match_id: str) -> List[int]:
	# Does not work properly
	# FIXME: https://github.com/nextcord/nextcord/issues/576
	if (qc := queue_channels.get(interaction.channel_id)) is None:
		return []
	return [m.id for m in active_matches if m.qc == qc and str(m.id).startswith(match_id)]


async def teams_by_author(interaction: Interaction, name: str) -> List[str]:
	if (match := find(lambda m: interaction.user in m.players, active_matches)) is not None:
		return [team.name for team in match.teams[:2] if team.name.startswith(name)]
	return ['active match not found']


async def teams_by_match_id(interaction: Interaction, name: str) -> List[str]:
	interaction_match = find(lambda i: i['name'] == 'match_id', interaction.data['options'][0]['options'])
	if interaction_match and (match := get(active_matches, id=interaction_match['value'])):
		return [team.name for team in match.teams[:2] if team.name.startswith(name)]
	return ['incorrect match_id supplied']
