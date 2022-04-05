# -*- coding: utf-8 -*-

from .main import update_qc_lang, active_matches, active_queues, update_rating_system, waiting_reactions, save_state
from .main import load_state, enable_channel, disable_channel, queue_channels, allow_offline, last_match_id
from .main import remove_players, auto_ready, expire_auto_ready

from .queue_channel import QueueChannel
from .queues.pickup_queue import PickupQueue
from .queues.common import QueueResponses as Qr
from .match.match import Match
from .expire import expire
from .stats import stats
from .stats.noadds import noadds
from .exceptions import Exceptions as Exc
from .context import Context, SlashContext, SystemContext
from . import commands

from . import events
from . import utils


def background_context(coro):
	async def wrapper(qc, *args, **kwargs):
		await coro(SystemContext(qc=qc), *args, **kwargs)
	return wrapper
