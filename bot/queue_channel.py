# -*- coding: utf-8 -*-
import re
import asyncio
from enum import Enum
from nextcord import Forbidden

from core.cfg_factory import CfgFactory, Variables, VariableTable
from core.locales import locales
from core.utils import join_and, seconds_to_str, get_nick
from core.database import db

import bot
from bot.stats.rating import FlatRating, Glicko2Rating, TrueSkillRating

MAX_EXPIRE_TIME = 12*60*60
MAX_PROMOTION_DELAY = 12*60*60


class Perms(Enum):
	MEMBER = 0
	MODERATOR = 1
	ADMIN = 2


class QueueChannel:

	rating_names = {
		'flat': FlatRating,
		'Glicko2': Glicko2Rating,
		'TrueSkill': TrueSkillRating
	}

	cfg_factory = CfgFactory(
		"qc_configs",
		p_key="channel_id",
		sections=["General", "Auto-remove", "Rating", "Leaderboard"],
		variables=[
			Variables.StrVar(
				"prefix",
				display="Command prefix",
				section="General",
				description="Set the prefix before for the bot`s commands",
				verify=lambda x: len(x) == 1,
				verify_message="Command prefix must be exactly one symbol.",
				default="!",
				notnull=True
			),
			Variables.OptionVar(
				"lang",
				display="Language",
				section="General",
				description="Select bot translation language",
				options=locales.keys(),
				default="en",
				notnull=True,
				on_change=bot.update_qc_lang
			),
			Variables.RoleVar(
				"admin_role",
				display="Admin role",
				section="General",
				description="Members with this role will be able to change the bot`s settings and use moderation commands."
			),
			Variables.RoleVar(
				"moderator_role",
				display="Moderator role",
				section="General",
				description="Members with this role will be able to use the bot`s moderation commands."
			),
			Variables.RoleVar(
				"promotion_role",
				display="Promotion role",
				section="General",
				description="Set a role to highlight on !promote and !sub commands.",
			),
			Variables.DurationVar(
				"promotion_delay",
				display="Promotion delay",
				section="General",
				description="Set time delay between players can promote queues.",
				verify=lambda x: 0 <= MAX_PROMOTION_DELAY,
				verify_message=f"Promotion delay time must be less than {seconds_to_str(MAX_EXPIRE_TIME)}"
			),
			Variables.BoolVar(
				"remove_afk",
				display="Auto remove on AFK status",
				section="Auto-remove",
				default=1,
				notnull=True
			),
			Variables.BoolVar(
				"remove_offline",
				display="Auto remove on offline status",
				section="Auto-remove",
				default=1,
				notnull=True
			),
			Variables.DurationVar(
				"expire_time",
				display="Auto remove on timer after last !add command",
				section="Auto-remove",
				verify=lambda x: 0 < x <= MAX_EXPIRE_TIME,
				verify_message=f"Expire time must be less than {seconds_to_str(MAX_EXPIRE_TIME)}"
			),
			Variables.RoleVar(
				"blacklist_role",
				display="Blacklist role",
				section="General",
				description="Players with this role wont be able to add to queues.",
			),
			Variables.RoleVar(
				"whitelist_role",
				display="Whitelist role",
				section="General",
				description="If set, only players with this role will be able to add to queues."
			),
			Variables.DurationVar(
				"max_auto_ready",
				display="Auto ready limit",
				section="General",
				description="Set limit on how long !auto_ready duration can be. Disable to prohibit the command.",
				default=15*60,
				verify=lambda d: 0 < d < 86401,
				verify_message="Auto ready limit must be 24 hours or less."
			),
			Variables.TextVar(
				"description",
				display="Description",
				section="General",
				description="Set an answer on '!help' command."
			),
			Variables.OptionVar(
				"rating_system",
				display="Rating system",
				section="Rating",
				description="Set player's rating calculation method.",
				options=rating_names.keys(),
				default="TrueSkill",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.TextChanVar(
				"rating_channel",
				display="Rating host channel",
				section="Rating",
				description="Use rating data from another channel.",
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_initial",
				display="Initial rating",
				section="Rating",
				description="Set player's initial rating.",
				default=1500,
				verify=lambda x: 0 <= x <= 10000,
				verify_message="Initial rating must be between 0 and 10000",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_deviation",
				display="Initial deviation",
				section="Rating",
				description="Set player's initial rating deviation.",
				default=200,
				verify=lambda x: 1 <= x <= 3000,
				verify_message="Rating deviation must be between 1 and 3000",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_min_deviation",
				display="Minimum deviation",
				section="Rating",
				description="Set players minimum deviation value. If not set, rating changes may seek to 0 over time.",
				default=75,
				verify=lambda x: 1 <= x <= 3000,
				verify_message="Rating minimum deviation must be between 1 and 3000",
				on_change=bot.update_rating_system
			),
			Variables.SliderVar(
				"rating_scale",
				display="Rating scale",
				section="Rating",
				max_val=1000,
				description="Scale all rating changes, 100% = x1.",
				on_change=bot.update_rating_system
			),
			Variables.SliderVar(
				"rating_loss_scale",
				display="Rating loss scale",
				section="Rating",
				description="\n".join([
					"Scale rating changes for losses, 100% = x1.",
					"Warning: changing this will break ratings balance."
				]),
				max_val=500,
				on_change=bot.update_rating_system
			),
			Variables.SliderVar(
				"rating_win_scale",
				display="Rating win scale",
				section="Rating",
				description="\n".join([
					"Scale rating changes for wins, 100% = x1.",
					"Warning: changing this will break ratings balance."
				]),
				max_val=500,
				on_change=bot.update_rating_system
			),
			Variables.SliderVar(
				"rating_draw_bonus",
				display="Rating draw bonus",
				section="Rating",
				description="\n".join([
					"Add rating bonus for draws.",
					"100% = x + 1x // -100% = x - 1x",
					"Warning: changing this will break ratings balance."
				]),
				max_val=500,
				min_val=-500,
				on_change=bot.update_rating_system
			),
			Variables.BoolVar(
				"rating_ws_boost",
				display="Rating winning streak boost",
				section="Rating",
				description="Apply rating boost from 1.5x to 3x from 3 to 6 won matches in a row.",
				notnull=True,
				default=0,
				on_change=bot.update_rating_system
			),
			Variables.BoolVar(
				"rating_ls_boost",
				display="Rating losing streak boost",
				section="Rating",
				description="Apply rating boost from 1.5x to 3x from 3 to 6 lost matches in a row.",
				notnull=True,
				default=0,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_decay",
				display="Rating decay",
				section="Rating",
				description="Set weekly rating decay until a nearest rank is met. Applies only to inactive players.",
				default=15,
				verify=lambda x: 0 <= x <= 100,
				verify_message="Rating decay must be between 0 and 100",
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_deviation_decay",
				display="Rating deviation decay",
				section="Rating",
				description="Set weekly rating deviation decay until initial deviation is met. Applies to all players.",
				default=15,
				verify=lambda x: 0 <= x <= 500,
				verify_message="Rating deviation decay must be between 0 and 500",
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"lb_min_matches",
				display="Leaderboard min matches",
				section="Leaderboard",
				description="Set a minimum amount of played matches required for a player to be shown in the !leaderboard."
			),
			Variables.BoolVar(
				"rating_nicks",
				display="Set ratings to nicks",
				section="Leaderboard",
				description="Add [rating] prefix to guild members nicknames.",
				default=0,
				notnull=True
			)
		],
		tables=[
			VariableTable(
				'ranks', display="Rating ranks", section="Leaderboard",
				variables=[
					Variables.StrVar("rank", default="〈E〉"),
					Variables.IntVar("rating", default=1200, description="The rank will be given on this rating or higher."),
					Variables.RoleVar("role", description="Assign a guild role to the rank owners.")
				],
				default=[
					dict(rank="〈G〉", rating=0, role=None),
					dict(rank="〈F〉", rating=1000, role=None),
					dict(rank="〈E〉", rating=1200, role=None),
					dict(rank="〈D〉", rating=1400, role=None),
					dict(rank="〈C〉", rating=1600, role=None),
					dict(rank="〈B〉", rating=1800, role=None),
					dict(rank="〈A〉", rating=1900, role=None),
					dict(rank="〈★〉", rating=2000, role=None)
				],
				blank=dict(rank="〈G〉", rating=0, role=None)
			)
		]
	)

	@classmethod
	async def create(cls, text_channel):
		"""
		This method is used for creating new QueueChannel objects because __init__() cannot call async functions.
		"""

		qc_cfg = await cls.cfg_factory.spawn(text_channel.guild, p_key=text_channel.id)
		self = cls(text_channel, qc_cfg)

		for pq_cfg in await bot.PickupQueue.cfg_factory.select(text_channel.guild, {"channel_id": self.id}):
			self.queues.append(bot.PickupQueue(self, pq_cfg))

		return self

	def __init__(self, text_channel, qc_cfg):
		self.cfg = qc_cfg
		self.id = text_channel.id
		self.channel = text_channel
		self.gt = locales[self.cfg.lang]
		self.rating = self.rating_names[self.cfg.rating_system](
			channel_id=(self.cfg.rating_channel or text_channel).id,
			init_rp=self.cfg.rating_initial,
			init_deviation=self.cfg.rating_deviation,
			min_deviation=self.cfg.rating_min_deviation,
			loss_scale=self.cfg.rating_loss_scale,
			win_scale=self.cfg.rating_win_scale,
			draw_bonus=self.cfg.rating_draw_bonus,
			ws_boost=self.cfg.rating_ws_boost,
			ls_boost=self.cfg.rating_ls_boost
		)
		self.queues = []
		self.last_promote = 0

	async def update_info(self, text_channel):
		self.cfg.cfg_info['channel_name'] = text_channel.name
		self.cfg.cfg_info['guild_id'] = text_channel.guild.id
		self.cfg.cfg_info['guild_name'] = text_channel.guild.name

		await self.cfg.set_info(self.cfg.cfg_info)

	def update_lang(self):
		self.gt = locales[self.cfg.lang]

	def update_rating_system(self):
		self.rating = self.rating_names[self.cfg.rating_system](
			channel_id=(self.cfg.rating_channel or self).id,
			init_rp=self.cfg.rating_initial,
			init_deviation=self.cfg.rating_deviation,
			min_deviation=self.cfg.rating_min_deviation,
			scale=self.cfg.rating_scale,
			loss_scale=self.cfg.rating_loss_scale,
			win_scale=self.cfg.rating_win_scale,
			draw_bonus=self.cfg.rating_draw_bonus,
			ws_boost=self.cfg.rating_ws_boost,
			ls_boost=self.cfg.rating_ls_boost
		)

	async def apply_rating_decay(self):
		if self.id == self.rating.channel_id and (self.cfg.rating_decay or self.cfg.rating_deviation_decay):
			await self.rating.apply_decay(self.cfg.rating_decay or 0, self.cfg.rating_deviation_decay or 0, self._ranks_table)

	@property
	def _ranks_table(self):
		if self.cfg.rating_channel:
			return (bot.queue_channels.get(self.cfg.rating_channel.id) or self).cfg.tables.ranks
		else:
			return self.cfg.tables.ranks

	async def new_queue(self, name, size, kind):
		kind.validate_name(name)
		if 1 > size > 100:
			raise ValueError("Queue size must be between 2 and 100.")
		if name.lower() in [i.name.lower() for i in self.queues]:
			raise ValueError("Queue with this name already exists.")

		q_obj = await kind.create(self, name, size)
		self.queues.append(q_obj)
		return q_obj

	@property
	def topic(self):
		populated = [q for q in self.queues if len(q.queue)]
		if not len(populated):
			return f"> {self.gt('no players')}"
		elif len(populated) < 5:
			return "\n".join([f"> **{q.name}** ({q.status}) | {q.who}" for q in populated])
		else:
			return "> [" + " | ".join([f"**{q.name}** ({q.status})" for q in populated]) + "]"

	async def remove_members(self, *members, ctx=None, reason=None, highlight=False):
		affected = set()
		for q in (q for q in self.queues if q.length):
			affected.update(q.pop_members(*members))

		if len(affected):
			if not ctx:
				ctx = bot.SystemContext(self)

			for m in affected:
				bot.expire.cancel(self, m)
			if reason:
				await ctx.notice(self.topic)
				if highlight:
					mention = join_and([m.mention for m in affected])
				else:
					mention = join_and(['**' + get_nick(m) + '**' for m in affected])
				if reason == "expire":
					reason = self.gt("expire time ran off")
				elif reason == "offline":
					reason = self.gt("member offline")
				elif reason == "afk":
					reason = self.gt("member AFK")
				elif reason == "left guild":
					reason = self.gt("member left the guild")
				elif reason == "pickup started":
					reason = self.gt("queue started on another channel")
				elif reason == "moderator":
					reason = self.gt("removed by a moderator")

				if len(affected) == 1:
					await ctx.notice(self.gt("{member} were removed from all queues ({reason}).").format(
						member=mention,
						reason=reason
					))
				else:
					await ctx.notice(self.gt("{members} were removed from all queues ({reason}).").format(
						members=mention,
						reason=reason
					))
		elif reason and ctx:
			await ctx.ignore(self.gt("Action had no effect"))

	def rating_rank(self, rating):
		table = self._ranks_table
		below = sorted(
			(rank for rank in table if rank['rating'] <= rating),
			key=lambda r: r['rating'], reverse=True
		)
		if not len(below):
			return {'rank': '〈?〉', 'rating': 0, 'role': None}
		return below[0]

	async def get_lb(self):
		data = await db.select(
			['user_id', 'nick', 'rating', 'deviation', 'wins', 'losses', 'draws', 'streak', 'is_hidden'], 'qc_players',
			where={'channel_id': self.rating.channel_id}, order_by="rating"
		)
		return [
			i for i in data
			if i['rating'] is not None
			and not i['is_hidden']
			and not (self.cfg.lb_min_matches and self.cfg.lb_min_matches > sum((i['wins'], i['losses'], i['draws'])))
		]

	async def update_rating_roles(self, *members):
		asyncio.create_task(self._update_rating_roles(*members))

	async def update_expire(self, member):
		""" update expire timer on !add command """
		personal_expire = await db.select_one(['expire'], 'players', where={'user_id': member.id})
		personal_expire = personal_expire.get('expire') if personal_expire else None
		if personal_expire not in [0, None]:
			bot.expire.set(self, member, personal_expire)
		elif self.cfg.expire_time and personal_expire is None:
			bot.expire.set(self, member, self.cfg.expire_time)

	async def _update_rating_roles(self, *members):
		table = self._ranks_table
		data = await self.rating.get_players((i.id for i in members))
		roles = {i['user_id']: self.rating_rank(i['rating'])['role'] for i in data}
		ratings = {i['user_id']: i['rating'] for i in data}
		all_roles = [i['role'] for i in table if i is not None]

		for member in members:
			to_delete = [role for role in all_roles if role != roles[member.id] and role in member.roles]
			try:
				if len(to_delete):
					await member.remove_roles(*to_delete, reason="Rank update.")
				if roles[member.id] is not None and roles[member.id] not in member.roles:
					await member.add_roles(roles[member.id], reason="Rank update.")
				if self.cfg.rating_nicks:
					if member.nick and (x := re.match(r"^\[\d+\] (.+)", member.nick)):
						await member.edit(nick=f"[{ratings[member.id]}] " + x.group(1))
					else:
						await member.edit(nick=f"[{ratings[member.id]}] " + (member.nick or member.name))
			except Forbidden:
				pass

			await asyncio.sleep(1)

	async def queue_started(self, ctx, members, message=None):
		await self.remove_members(*members, ctx=ctx)

		for m in filter(lambda m: m.id in bot.allow_offline, members):
			bot.allow_offline.remove(m.id)
		if message:
			asyncio.create_task(self._dm_members(members, message))

		await bot.remove_players(*members, reason="pickup started")

	async def _dm_members(self, members, *args, **kwargs):
		for m in members:
			if not m.bot and not await db.select_one(("user_id", ), "players", where={'user_id': m.id, 'allow_dm': 0}):
				try:
					await m.send(*args, **kwargs)
				except Forbidden:
					pass
				await asyncio.sleep(1)

	async def check_allowed_to_add(self, member, queue=None):
		""" raises exception if not allowed, returns phrase string or None if allowed """

		if self.cfg.blacklist_role and self.cfg.blacklist_role in member.roles:
			raise bot.Exc.PermissionError(self.gt("You are not allowed to add to queues on this channel."))
		if self.cfg.whitelist_role and self.cfg.whitelist_role not in member.roles:
			raise bot.Exc.PermissionError(self.gt("You are not allowed to add to queues on this channel."))

		ban_left, phrase = await bot.noadds.get_user(self, member)
		if ban_left:
			raise bot.Exc.PermissionError(self.gt("You have been banned, `{duration}` left.").format(
				duration=seconds_to_str(ban_left)
			))

		if any((member in m.players for m in bot.active_matches)):
			raise bot.Exc.InMatchError(self.gt("You are already in an active match."))

		if queue:
			await queue.check_allowed_to_add(member)
		return phrase
