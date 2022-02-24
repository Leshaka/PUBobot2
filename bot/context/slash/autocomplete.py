from typing import List
from nextcord import Interaction

from core.utils import find, get

from bot import QueueChannel, queue_channels


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
	interaction_queue = find(lambda i: i['name'] == 'queue', interaction.data['options'])
	if interaction_queue and (queue := get(qc.queues, name=interaction_queue['value'])):
		return sorted([v for v in queue.cfg_factory.variables.keys() if v.startswith(variable)])[:10]
	return []
