# -*- coding: utf-8 -*-

from .main import update_qc_lang, update_rating_system, save_state
from .main import load_state, enable_channel, disable_channel
from .main import remove_players, expire_auto_ready

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

bot_was_ready = False
bot_ready = False
queue_channels = dict()  # {channel.id: QueueChannel()}
active_queues = []
active_matches = []
waiting_reactions = dict()  # {message.id: function}
allow_offline = []  # [user_id]
auto_ready = dict()  # {user.id: timestamp}


def background_context(coro):
	async def wrapper(qc, *args, **kwargs):
		await coro(SystemContext(qc=qc), *args, **kwargs)
	return wrapper
