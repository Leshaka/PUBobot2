# -*- coding: utf-8 -*-
import re
import json
import time
import asyncio
import traceback
from random import randint, choice
from discord import Embed, Colour, Forbidden

from core.config import cfg
from core.console import log
from core.cfg_factory import CfgFactory, Variables, VariableTable
from core.locales import locales
from core.utils import error_embed, ok_embed, find, get, join_and, seconds_to_str, parse_duration, get_nick, discord_table
from core.database import db
from core.client import FakeMember

import bot
from bot.stats.rating import FlatRating, Glicko2Rating, TrueSkillRating

MAX_EXPIRE_TIME = 12*60*60
MAX_PROMOTION_DELAY = 12*60*60


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

		for pq_cfg in await bot.PickupQueue.cfg_factory.select(text_channel.guild, {"channel_id": self.channel.id}):
			self.queues.append(bot.PickupQueue(self, pq_cfg))

		return self

	def __init__(self, text_channel, qc_cfg):
		self.cfg = qc_cfg
		self.id = text_channel.id
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
		self.channel = text_channel
		self.topic = f"> {self.gt('no players')}"
		self.last_promote = 0
		self.commands = dict(
			create_pickup=self._create_pickup,
			delete_queue=self._delete_queue,
			queues=self._show_queues,
			pickups=self._show_queues,
			add=self._add_member,
			j=self._add_member,
			remove=self._remove_member,
			l=self._remove_member,
			who=self._who,
			set=self._set,
			set_queue=self._set_queue,
			cfg=self._cfg,
			cfg_queue=self._cfg_queue,
			set_cfg=self._set_cfg,
			set_cfg_queue=self._set_cfg_queue,
			r=self._ready,
			ready=self._ready,
			nr=self._not_ready,
			not_ready=self._not_ready,
			auto_ready=self._auto_ready,
			ar=self._auto_ready,
			capfor=self._cap_for,
			pick=self._pick,
			p=self._pick,
			teams=self._teams,
			put=self._put,
			subme=self._sub_me,
			subfor=self._sub_for,
			subforce=self._sub_force,
			rank=self._rank,
			lb=self._leaderboard,
			leaderboard=self._leaderboard,
			rl=self._rl,
			report_loss=self._rl,
			rd=self._rd,
			report_draw=self._rd,
			rc=self._rc,
			report_cancel=self._rc,
			rw=self._rw,
			report_win=self._rw,
			report_manual=self._report_manual,
			expire=self._expire,
			default_expire=self._default_expire,
			ao=self._allow_offline,
			allow_offline=self._allow_offline,
			matches=self._matches,
			promote=self._promote,
			rating_set=self._rating_set,
			seed=self._rating_set,
			rating_penality=self._rating_penality,
			rating_hide=self._rating_hide,
			rating_unhide=self._rating_unhide,
			rating_reset=self._rating_reset,
			rating_snap=self._rating_snap,
			cancel_match=self._cancel_match,
			undo_match=self._undo_match,
			switch_dms=self._switch_dms,
			start=self._start,
			stats_reset=self._stats_reset,
			stats_reset_player=self._stats_reset_player,
			stats_replace_player=self._stats_replace_player,
			lastgame=self._last_game,
			lg=self._last_game,
			commands=self._commands,
			reset=self._reset,
			remove_player=self._remove_player,
			add_player=self._add_player,
			subscribe=self._subscribe,
			unsubscribe=self._unsubscribe,
			server=self._server,
			ip=self._server,
			stats=self._stats,
			top=self._top,
			cointoss=self._cointoss,
			ct=self._cointoss,
			help=self._help,
			maps=self._maps,
			map=self._map,
			noadds=self._noadds,
			noadd=self._noadd,
			forgive=self._forgive,
			phrases_add=self._phrases_add,
			phrases_clear=self._phrases_clear,
			nick=self._set_nick
		)

	async def update_info(self):
		self.cfg.cfg_info['channel_name'] = self.channel.name
		self.cfg.cfg_info['guild_id'] = self.channel.guild.id
		self.cfg.cfg_info['guild_name'] = self.channel.guild.name

		await self.cfg.set_info(self.cfg.cfg_info)

	def update_lang(self):
		self.gt = locales[self.cfg.lang]

	def update_rating_system(self):
		self.rating = self.rating_names[self.cfg.rating_system](
			channel_id=(self.cfg.rating_channel or self.channel).id,
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

	def access_level(self, member):
		if (self.cfg.admin_role in member.roles or
					member.id == cfg.DC_OWNER_ID or
					self.channel.permissions_for(member).administrator):
			return 2
		elif self.cfg.moderator_role in member.roles:
			return 1
		else:
			return 0

	def _check_perms(self, member, req_perms):
		if self.access_level(member) < req_perms:
			if req_perms == 2:
				raise bot.Exc.PermissionError(self.gt("You must possess admin permissions."))
			else:
				raise bot.Exc.PermissionError(self.gt("You must possess moderator permissions."))

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

	async def update_topic(self, force_announce=False, phrase=None):
		populated = [q for q in self.queues if len(q.queue)]
		if not len(populated):
			new_topic = f"> {self.gt('no players')}"
		elif len(populated) < 5:
			new_topic = "\n".join([f"> **{q.name}** ({q.status}) | {q.who}" for q in populated])
		else:
			new_topic = "> [" + " | ".join([f"**{q.name}** ({q.status})" for q in populated]) + "]"
		if new_topic != self.topic or force_announce:
			self.topic = new_topic
			if phrase:
				await self.channel.send(phrase + "\n" + self.topic)
			else:
				await self.channel.send(self.topic)

	async def auto_remove(self, member):
		if member.id in bot.allow_offline:
			return
		if bot.expire.get(self, member) is None:
			if str(member.status) == "idle" and self.cfg.remove_afk:
				await self.remove_members(member, reason="afk", highlight=True)
		if str(member.status) == "offline" and self.cfg.remove_offline:
			await self.remove_members(member, reason="offline")

	async def remove_members(self, *members, reason=None, highlight=False):
		affected = set()
		for q in (q for q in self.queues if q.length):
			affected.update(q.pop_members(*members))

		if len(affected):
			for m in affected:
				bot.expire.cancel(self, m)
			await self.update_topic()
			if reason:
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
					await self.channel.send(self.gt("{member} were removed from all queues ({reason}).").format(
						member=mention,
						reason=reason
					))
				else:
					await self.channel.send(self.gt("{members} were removed from all queues ({reason}).").format(
						members=mention,
						reason=reason
					))

	async def error(self, content, title=None, reply_to=None):
		title = title or self.gt("Error")
		if reply_to:
			content = f"<@{reply_to.id}>, " + content
		await self.channel.send(embed=error_embed(content, title=title))

	async def success(self, content, title=None, reply_to=None):
		# title = title or self.gt("Success")
		if reply_to:
			content = f"<@{reply_to.id}>, " + content
		await self.channel.send(embed=ok_embed(content, title=title))

	def get_match(self, member):
		for match in bot.active_matches:
			if match.qc is self and member in match.players:
				return match
		return None

	def get_member(self, string):
		if highlight := re.match(r"<@!?(\d+)>", string):
			return self.channel.guild.get_member(int(highlight.group(1)))
		elif mask := re.match(r"^(\w+)@(\d{5,20})$", string):
			name, user_id = mask.groups()
			return FakeMember(guild=self.channel.guild, user_id=int(user_id), name=name)
		else:
			string = string.lower()
			return find(
				lambda m: string == m.name.lower() or (m.nick and string == m.nick.lower()),
				self.channel.guild.members
			)

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
				print(traceback.format_exc())
			await asyncio.sleep(1)

	async def queue_started(self, members, message=None):
		await self.remove_members(*members)

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

	async def process_msg(self, message):
		if not len(message.content) > 1:
			return

		cmd = message.content.split(' ', 1)[0].lower()

		# special commands
		if re.match(r"^\+..", cmd):
			f, args = self.commands.get('add'), [message.content[1:]]
		elif re.match(r"^-..", cmd):
			f, args = self.commands.get('remove'), [message.content[1:]]
		elif cmd == "++":
			f, args = self.commands.get('add'), []
		elif cmd == "--":
			f, args = self.commands.get('remove'), []

		# normal commands starting with prefix
		elif self.cfg.prefix == cmd[0]:
			if await db.select_one(['guild_id'], 'disabled_guilds', where={'guild_id': self.channel.guild.id}):
				await self.error(
					f"This guild is disabled.\nPlease check {cfg.WS_ROOT_URL}/main/{self.channel.guild.id}/_billing"
				)
				return
			f, args = self.commands.get(cmd[1:]), message.content.split(' ', 1)[1:]
		else:
			return

		if f:
			log.command("{} | #{} | {}: {}".format(
				self.channel.guild.name, self.channel.name, get_nick(message.author), message.content
			))
			try:
				await f(message, *args)
			except bot.Exc.PubobotException as e:
				await message.channel.send(embed=error_embed(str(e), title=type(e).__name__))
			except BaseException as e:
				await message.channel.send(embed=error_embed(str(e), title="RuntimeError"))
				log.error(f"Error processing last message. Traceback:\n{traceback.format_exc()}======")

	#  Bot commands #

	async def _create_pickup(self, message, args=""):
		self._check_perms(message.author, 2)
		args = args.split(" ")
		if len(args) != 2 or not args[1].isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}create_pickup __name__ __size__")
		try:
			pq = await self.new_queue(args[0], int(args[1]), bot.PickupQueue)
		except ValueError as e:
			raise bot.Exc.ValueError(str(e))
		else:
			await self.success(f"[**{pq.name}** ({pq.status})]")

	async def _delete_queue(self, message, args=None):
		self._check_perms(message.author, 2)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}delete_queue __name__")
		if (queue := get(self.queues, name=args)) is None:
			raise bot.Exc.NotFoundError(f"Specified queue name not found on the channel.")
		await queue.cfg.delete()
		self.queues.remove(queue)
		await self._show_queues(message, args=None)

	async def _show_queues(self, message, args=None):
		if len(self.queues):
			await self.channel.send("> [" + " | ".join(
				[f"**{q.name}** ({q.status})" for q in self.queues]
			) + "]")
		else:
			await self.channel.send("> [ **no queues configured** ]")

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


	async def _add_member(self, message, args=None):
		phrase = await self.check_allowed_to_add(message.author)

		targets = args.lower().split(" ") if args else []

		# select the only one queue on the channel
		if not len(targets) and len(self.queues) == 1:
			t_queues = self.queues

		# select queues requested by user
		elif len(targets):
			t_queues = [q for q in self.queues if any(
				(t == q.name.lower() or t in (a["alias"].lower() for a in q.cfg.tables.aliases) for t in targets)
			)]

		# select active queues or default queues if no active queues
		else:
			t_queues = [q for q in self.queues if len(q.queue) and q.cfg.is_default]
			if not len(t_queues):
				t_queues = [q for q in self.queues if q.cfg.is_default]

		qr = dict()  # get queue responses
		for q in t_queues:
			qr[q] = await q.add_member(message.author)
			if qr[q] == bot.Qr.QueueStarted:
				return

		if len(not_allowed := [q for q in qr.keys() if qr[q] == bot.Qr.NotAllowed]):
			await self.error(self.gt("You are not allowed to add to {queues} queues.".format(
				queues=join_and([f"**{q.name}**" for q in not_allowed])
			)))

		if bot.Qr.Success in qr.values():
			await self.update_expire(message.author)
			await self.update_topic(phrase=f"{message.author.mention}, {phrase}" if phrase else None)

	async def _remove_member(self, message, args=None):
		targets = args.lower().split(" ") if args else []

		if not len(targets):
			await self.remove_members(message.author)
			return

		t_queues = (q for q in self.queues if any(
			(t == q.name.lower() or t in (a["alias"].lower() for a in q.cfg.tables.aliases) for t in targets)
		))

		for q in t_queues:
			q.pop_members(message.author)

		if not any((q.is_added(message.author) for q in self.queues)):
			bot.expire.cancel(self, message.author)

		await self.update_topic()

	async def _who(self, message, args=None):
		targets = args.lower().split(" ") if args else []

		if len(targets):
			t_queues = [q for q in self.queues if any(
				(t == q.name.lower() or t in (a["alias"].lower() for a in q.cfg.tables.aliases) for t in targets)
			)]
		else:
			t_queues = [q for q in self.queues if len(q.queue)]

		if not len(t_queues):
			await self.channel.send(f"> {self.gt('no players')}")
		else:
			await self.channel.send("\n".join([f"> **{q.name}** ({q.status}) | {q.who}" for q in t_queues]))

	async def _set(self, message, args=""):
		self._check_perms(message.author, 2)
		args = args.split(" ", maxsplit=2)
		if len(args) != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}set __variable__ __value__")

		var_name = args[0].lower()
		if var_name not in self.cfg_factory.variables.keys():
			raise bot.Exc.SyntaxError(f"No such variable '{var_name}'.")
		try:
			await self.cfg.update({var_name: args[1]})
		except Exception as e:
			raise bot.Exc.ValueError(str(e))
		else:
			await self.success(f"Variable __{var_name}__ configured.")

	async def _set_queue(self, message, args=""):
		self._check_perms(message.author, 2)
		args = args.split(" ", maxsplit=2)
		if len(args) != 3:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}set_queue __queue__ __variable__ __value__")
		if (queue := find(lambda q: q.name.lower() == args[0].lower(), self.queues)) is None:
			raise bot.Exc.SyntaxError("Specified queue not found.")
		if (var_name := args[1].lower()) not in queue.cfg_factory.variables.keys():
			raise bot.Exc.SyntaxError(f"No such variable '{var_name}'.")

		try:
			await queue.cfg.update({var_name: args[2]})
		except Exception as e:
			raise bot.Exc.ValueError(str(e))
		else:
			await self.success(f"Variable __{var_name}__ configured.")

	async def _cfg(self, message, args=None):
		await message.author.send(f"```json\n{json.dumps(self.cfg.to_json(), ensure_ascii=False, indent=2)}```")

	async def _cfg_queue(self, message, args=None):
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}cfg_queue __queue__")

		args = args.lower()
		for q in self.queues:
			if q.name.lower() == args:
				await message.author.send(f"```json\n{json.dumps(q.cfg.to_json(), ensure_ascii=False, indent=2)}```")
				return
		raise bot.Exc.SyntaxError(f"No such queue '{args}'.")

	async def _set_cfg(self, message, args=None):
		self._check_perms(message.author, 2)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}set_cfg __json__")
		try:
			await self.cfg.update(json.loads(args))
		except Exception as e:
			raise bot.Exc.ValueError(str(e))
		else:
			await self.success(f"Channel configuration updated.")

	async def _set_cfg_queue(self, message, args=""):
		self._check_perms(message.author, 2)
		args = args.split(" ", maxsplit=1)
		if len(args) != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}set_cfg_queue __queue__ __json__")

		for q in self.queues:
			if q.name.lower() == args[0].lower():
				try:
					await q.cfg.update(json.loads(args[1]))
				except Exception as e:
					raise bot.Exc.ValueError(str(e))
				else:
					await self.success(f"__{q.name}__ queue configuration updated.")
				return
		raise bot.Exc.SyntaxError(f"No such queue '{args}'.")

	async def _ready(self, message, args=None):
		if match := self.get_match(message.author):
			await match.check_in.set_ready(message.author, True)
		else:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))

	async def _not_ready(self, message, args=None):
		if match := self.get_match(message.author):
			await match.check_in.set_ready(message.author, False)
		else:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))

	async def _auto_ready(self, message, args=None):
		if not self.cfg.max_auto_ready:
			raise bot.Exc.PermissionError(self.gt("!auto_ready command is turned off on this channel."))
		if args:
			try:
				secs = parse_duration(args)
			except ValueError:
				raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}auto_ready [__duration__]")
			if secs > self.cfg.max_auto_ready:
				raise bot.Exc.ValueError(self.gt("Maximum auto_ready duration is {duration}.").format(
					duration=seconds_to_str(self.cfg.max_auto_ready)
				))
		else:
			secs = min([60*5, self.cfg.max_auto_ready])

		if message.author.id in bot.auto_ready.keys():
			bot.auto_ready.pop(message.author.id)
			await self.success(self.gt("Your automatic ready confirmation is now turned off."))
		else:
			bot.auto_ready[message.author.id] = int(time.time())+secs
			await self.success(
				self.gt("During next {duration} your match participation will be confirmed automatically.").format(
					duration=seconds_to_str(secs)
				))

	async def _cap_for(self, message, args=None):
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}capfor __team__")
		elif (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.draft.cap_for(message.author, args)

	async def _pick(self, message, args=None):
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}pick __player__")
		elif (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))

		members = [self.get_member(i.strip()) for i in args.strip().split(" ")]
		if None in members:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		await match.draft.pick(message.author, members)

	async def _teams(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.draft.print()

	async def _put(self, message, args=""):
		self._check_perms(message.author, 1)
		args = args.split(" ")
		if len(args) < 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}put __player__ __team__")
		elif (member := self.get_member(args[0])) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		elif (match := self.get_match(member)) is None:
			raise bot.Exc.NotInMatchError(self.gt("Specified user is not in a match."))
		await match.draft.put(member, args[1])

	async def _sub_me(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.draft.sub_me(message.author)

	async def _sub_for(self, message, args=None):
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}sub_for __@player__")
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		elif (match := self.get_match(member)) is None:
			raise bot.Exc.NotInMatchError(self.gt("Specified user is not in a match."))
		await self.check_allowed_to_add(message.author, queue=match.queue)
		await match.draft.sub_for(member, message.author)

	async def _sub_force(self, message, args=""):
		self._check_perms(message.author, 1)
		if len(args := args.split(" ")) != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}sub_force __@player1__ __@player2__")
		elif (member1 := self.get_member(args[0])) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		elif (member2 := self.get_member(args[1])) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		elif (match1 := self.get_match(member1)) is None:
			raise bot.Exc.NotInMatchError(self.gt("Specified user is not in a match."))
		elif self.get_match(member2) is not None:
			raise bot.Exc.InMatchError(self.gt("Specified user is in an active match."))

		await match1.draft.sub_for(member1, member2, force=True)

	async def _rank(self, message, args=None):
		if args:
			if (member := self.get_member(args)) is None:
				raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		else:
			member = message.author

		data = await self.get_lb()
		if p := find(lambda i: i['user_id'] == member.id, data):
			place = data.index(p)+1
		else:
			data = await db.select(
				['user_id', 'rating', 'deviation', 'channel_id', 'wins', 'losses', 'draws', 'is_hidden', 'streak'], "qc_players",
				where={'channel_id': self.rating.channel_id}
			)
			p = find(lambda i: i['user_id'] == member.id, data)
			place = "?"

		if p:
			embed = Embed(title=f"__{get_nick(member)}__", colour=Colour(0x7289DA))
			embed.add_field(name="№", value=f"**{place}**", inline=True)
			embed.add_field(name=self.gt("Matches"), value=f"**{(p['wins']+p['losses']+p['draws'])}**", inline=True)
			if p['rating']:
				embed.add_field(name=self.gt("Rank"), value=f"**{self.rating_rank(p['rating'])['rank']}**", inline=True)
				embed.add_field(name=self.gt("Rating"), value=f"**{p['rating']}**±{p['deviation']}")
			else:
				embed.add_field(name=self.gt("Rank"), value="**〈?〉**", inline=True)
				embed.add_field(name=self.gt("Rating"), value="**?**")
			embed.add_field(
				name="W/L/D/S",
				value="**{wins}**/**{losses}**/**{draws}**/**{streak}**".format(**p),
				inline=True
			)
			embed.add_field(name=self.gt("Winrate"), value="**{}%**\n\u200b".format(
				int(p['wins']*100 / (p['wins']+p['losses'] or 1))
			), inline=True)
			if member.avatar_url:
				embed.set_thumbnail(url=member.avatar_url)

			changes = await db.select(
				('at', 'rating_change', 'match_id', 'reason'),
				'qc_rating_history', where=dict(user_id=member.id, channel_id=self.rating.channel_id),
				order_by='id', limit=5
			)
			if len(changes):
				embed.add_field(
					name=self.gt("Last changes:"),
					value="\n".join(("\u200b \u200b **{change}** \u200b | {ago} ago | {reason}{match_id}".format(
						ago=seconds_to_str(int(time.time()-c['at'])),
						reason=c['reason'],
						match_id=f"(__{c['match_id']}__)" if c['match_id'] else "",
						change=("+" if c['rating_change'] >= 0 else "") + str(c['rating_change'])
					) for c in changes))
				)
			await self.channel.send(embed=embed)

		else:
			raise bot.Exc.ValueError(self.gt("No rating data found."))

	async def _rl(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.report_loss(message.author, draw_flag=False)

	async def _rd(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.report_loss(message.author, draw_flag=1)

	async def _rc(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.report_loss(message.author, draw_flag=2)

	async def _rw(self, message, args=""):
		self._check_perms(message.author, 1)
		args = args.split(" ", maxsplit=1)
		if len(args) != 2 or not args[0].isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rw __match_id__ __team_name__ or draw")
		if (match := find(lambda m: m.qc == self and m.id == int(args[0]), bot.active_matches)) is None:
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.").format(
				prefix=self.cfg.prefix
			))
		await match.report_win(args[1])

	async def _report_manual(self, message, args=""):
		self._check_perms(message.author, 1)
		args = args.split(" / ")
		queue = find(lambda q: q.name.lower() == args[0].lower(), self.queues)
		teams = [[self.get_member(p) for p in team.split(" ")] for team in args[1:]]
		if queue is None or len(teams) != 2 or None in teams[0] or None in teams[1]:
			raise bot.Exc.SyntaxError(
				f"Usage: {self.cfg.prefix}report_manual __queue__ / __won_team_players__ / __lost_team_players__"
			)
		await queue.fake_ranked_match(teams[0], teams[1])

	async def _expire(self, message, args=None):
		if not args:
			if task := bot.expire.get(self, message.author):
				await self.channel.send(self.gt("You have {duration} expire time left.").format(
					duration=seconds_to_str(task.at-int(time.time()))
				))
			else:
				await self.channel.send(self.gt("You don't have an expire timer set right now."))

		else:
			try:
				secs = parse_duration(args)
			except ValueError:
				raise bot.Exc.SyntaxError(self.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))

			if secs > MAX_EXPIRE_TIME:
				raise bot.Exc.ValueError(self.gt("Expire time must be less than {time}.".format(
					time=seconds_to_str(MAX_EXPIRE_TIME)
				)))

			bot.expire.set(self, message.author, secs)
			await self.success(self.gt("Set your expire time to {duration}.").format(
				duration=seconds_to_str(secs)
			))

	async def _default_expire(self, message, args=None):
		if not args:
			data = await db.select_one(['expire'], 'players', where={'user_id': message.author.id})
			expire = None if not data else data['expire']
			modify = False
		else:
			modify = True
			args = args.lower()
			if args == 'afk':
				expire = 0
			elif args == 'none':
				expire = None
			else:
				try:
					expire = parse_duration(args)
				except ValueError:
					raise bot.Exc.SyntaxError(self.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01 or AFK."))
				if expire > MAX_EXPIRE_TIME:
					raise bot.Exc.SyntaxError(self.gt("Expire time must be less than {time}.".format(
						time=seconds_to_str(MAX_EXPIRE_TIME)
					)))

		if expire == 0:
			text = self.gt("You will be removed from queues on AFK status by default.")
		elif expire is None:
			text = self.gt("Your expire time value will fallback to guild's settings.")
		else:
			text = self.gt("Your default expire time is {time}.".format(time=seconds_to_str(expire)))

		if not modify:
			await self.channel.send(text)
		else:
			try:
				await db.insert('players', {'user_id': message.author.id, 'expire': expire})
			except db.errors.IntegrityError:
				await db.update('players', {'expire': expire}, keys={'user_id': message.author.id})
			await self.success(text)

	async def _allow_offline(self, message, args=None):
		if message.author.id in bot.allow_offline:
			bot.allow_offline.remove(message.author.id)
			await self.success(self.gt("Your offline immunity is **off**."))
		else:
			bot.allow_offline.append(message.author.id)
			await self.success(self.gt("Your offline immunity is **on** until the next match."))

	async def _matches(self, message, args=0):
		try:
			page = int(args)
		except ValueError:
			page = 0

		matches = [m for m in bot.active_matches if m.qc.channel.id == self.channel.id]
		if len(matches):
			await self.channel.send("\n".join((m.print() for m in matches)))
		else:
			await self.channel.send(self.gt("> no active matches"))

	async def _leaderboard(self, message, args=1):
		try:
			page = int(args)-1
		except ValueError:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}lb [page]")

		data = (await self.get_lb())[page*10:(page+1)*10]

		if len(data):
			await self.channel.send(
				discord_table(
					["№", "Rating〈Ξ〉", "Nickname", "Matches", "W/L/D"],
					[[
						(page * 10) + (n + 1),
						str(data[n]['rating']) + self.rating_rank(data[n]['rating'])['rank'],
						data[n]['nick'].strip(),
						int(data[n]['wins'] + data[n]['losses'] + data[n]['draws']),
						"{0}/{1}/{2} ({3}%)".format(
							data[n]['wins'],
							data[n]['losses'],
							data[n]['draws'],
							int(data[n]['wins'] * 100 / ((data[n]['wins'] + data[n]['losses']) or 1))
						)
					] for n in range(len(data))]
				)
			)
		else:
			raise bot.Exc.NotFoundError(self.gt("Leaderboard is empty."))

	async def _promote(self, message, args=None):
		if not args:
			if (queue := next(iter(
					sorted((q for q in self.queues if q.length), key=lambda q: q.length, reverse=True)
			), None)) is None:
				raise bot.Exc.NotFoundError(self.gt("Nothing to promote."))
		else:
			if (queue := find(lambda q: q.name.lower() == args.lower(), self.queues)) is None:
				raise bot.Exc.NotFoundError(self.gt("Specified queue not found."))

		now = int(time.time())
		if self.cfg.promotion_delay and self.cfg.promotion_delay+self.last_promote > now:
			raise bot.Exc.PermissionError(self.gt("You're promoting too often, please wait `{delay}` until next promote.".format(
				delay=seconds_to_str((self.cfg.promotion_delay+self.last_promote)-now)
			)))

		await queue.promote()
		self.last_promote = now

	async def _rating_set(self, message, args=None):
		self._check_perms(message.author, 1)
		args = args.split(" ")
		try:
			if (member := self.get_member(args.pop(0))) is None:
				raise ValueError()
			rating = int(args.pop(0))
			if not 0 < rating < 10000:
				raise ValueError()
			deviation = int(args.pop(0)) if len(args) else None
		except (ValueError, IndexError):
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rating_set __@user__ __rating__ [__deviation__]")

		if not 0 < rating < 10000 or not 0 < (deviation or 1) < 3000:
			raise bot.Exc.ValueError("Bad rating or deviation value.")

		await self.rating.set_rating(member, rating=rating, deviation=deviation, reason="manual seeding")
		await self.update_rating_roles(member)
		await self.success(self.gt("Done."))

	async def _rating_penality(self, message, args=None):
		self._check_perms(message.author, 1)
		args = args.split(" ", maxsplit=2)
		try:
			if (member := self.get_member(args.pop(0))) is None:
				raise ValueError()
			penality = int(args.pop(0))
			if abs(penality) > 10000:
				raise ValueError()
		except (ValueError, IndexError):
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rating_penality __@user__ __points__ [__reason__]")

		reason = "penality: " + args[0] if len(args) else "penality by a moderator"
		await self.rating.set_rating(member, penality=penality, reason=reason)
		await self.update_rating_roles(member)
		await self.success(self.gt("Done."))

	async def _rating_hide(self, message, args=None):
		self._check_perms(message.author, 1)
		if (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rating_hide __@user__")
		await self.rating.hide_player(member.id)
		await self.success(self.gt("Done."))

	async def _rating_unhide(self, message, args=None):
		self._check_perms(message.author, 1)
		if (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rating_unhide __@user__")
		await self.rating.hide_player(member.id, hide=False)
		await self.success(self.gt("Done."))

	async def _rating_reset(self, message, args=None):
		self._check_perms(message.author, 2)
		await self.rating.reset()
		await self.success(self.gt("Done."))

	async def _rating_snap(self, message, args=None):
		self._check_perms(message.author, 2)
		await self.rating.snap_ratings(self._ranks_table)
		await self.success(self.gt("Done."))

	async def _cancel_match(self, message, args=""):
		self._check_perms(message.author, 1)
		if not args.isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}cancel_match __match_id__")

		if not (match := get(bot.active_matches, id=int(args))):
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.").format(
				prefix=self.cfg.prefix
			))
		if match.qc != self:
			raise bot.Exc.PermissionError("Specified match does not belong to this channel.")

		await match.cancel()

	async def _undo_match(self, message, args=""):
		self._check_perms(message.author, 1)
		if not args.isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}undo_match __match_id__")

		result = await bot.stats.undo_match(int(args), self)
		if result:
			await self.success(self.gt("Done."))
		else:
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.").format(
				prefix=self.cfg.prefix
			))

	async def _switch_dms(self, message, args=""):
		data = await db.select_one(('allow_dm', ), 'players', where={'user_id': message.author.id})
		if data:
			allow_dm = 1 if data['allow_dm'] == 0 else 0
			await db.update('players', {'allow_dm': allow_dm}, keys={'user_id': message.author.id})
		else:
			allow_dm = 0
			await db.insert('players', {'allow_dm': allow_dm, 'user_id': message.author.id})

		if allow_dm:
			await self.success(self.gt("Your DM notifications is now turned on."), reply_to=message.author)
		else:
			await self.success(self.gt("Your DM notifications is now turned off."), reply_to=message.author)

	async def _start(self, message, args=None):
		self._check_perms(message.author, 1)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}start __queue__")
		if (queue := find(lambda q: q.name.lower() == args.lower(), self.queues)) is None:
			raise bot.Exc.NotFoundError(self.gt("Specified queue not found."))
		await queue.start()

	async def _stats_reset(self, message, args=None):
		self._check_perms(message.author, 2)
		await bot.stats.reset_channel(self.channel.id)
		await self.success(self.gt("Done."))

	async def _stats_reset_player(self, message, args=None):
		self._check_perms(message.author, 1)
		if (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}stats_reset_player __@user__")
		await bot.stats.reset_player(self.channel.id, member.id)
		await self.success(self.gt("Done."))

	async def _stats_replace_player(self, message, args=""):
		self._check_perms(message.author, 1)
		if (args := args.split(" ")).__len__() != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}stats_reset_player __@user1__ __@user2__")
		if None in (members := [self.get_member(string) for string in args]):
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}stats_reset_player __@user1__ __@user2__")
		await bot.stats.replace_player(self.channel.id, members[0].id, members[1].id, get_nick(members[1]))
		await self.success(self.gt("Done."))

	async def _last_game(self, message, args=None):
		if args:
			if queue := find(lambda q: q.name.lower() == args.lower(), self.queues):
				last_game = await db.select_one(
					['*'], "qc_matches", where=dict(channel_id=self.id, queue_id=queue.id), order_by="match_id", limit=1
				)
			elif member := self.get_member(args):
				if match := await db.select_one(
					['match_id'], "qc_player_matches", where=dict(channel_id=self.id, user_id=member.id), order_by="match_id", limit=1
				):
					last_game = await db.select_one(
						['*'], "qc_matches", where=dict(channel_id=self.id, match_id=match['match_id'])
					)
				else:
					last_game = None
			else:
				raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}lastgame [__queue__]")
		else:
			last_game = await db.select_one(
				['*'], "qc_matches", where=dict(channel_id=self.id), order_by="match_id", limit=1
			)

		if not last_game:
			raise bot.Exc.NotFoundError(self.gt("Nothing found"))

		players = await db.select(['user_id', 'nick', 'team'], "qc_player_matches", where=dict(match_id=last_game['match_id']))
		embed = Embed(colour=Colour(0x50e3c2))
		embed.add_field(name=last_game['queue_name'], value=seconds_to_str(int(time.time())-last_game['at']) + " ago")
		if len(team := [p['nick'] for p in players if p['team'] == 0]):
			embed.add_field(name=last_game['alpha_name'], value="`"+", ".join(team)+"`")
		if len(team := [p['nick'] for p in players if p['team'] == 1]):
			embed.add_field(name=last_game['beta_name'], value="`" + ", ".join(team) + "`")
		if len(team := [p['nick'] for p in players if p['team'] is None]):
			embed.add_field(name=self.gt("Players"), value="`" + ", ".join(team) + "`")
		if last_game['ranked']:
			if last_game['winner'] is None:
				winner = 'Draw'
			else:
				winner = [last_game['alpha_name'], last_game['beta_name']][last_game['winner']]
			embed.add_field(name=self.gt("Winner"), value=winner)
		await self.channel.send(embed=embed)

	async def _commands(self, message, args=None):
		await self.channel.send(f"<{cfg.COMMANDS_URL}>")

	async def _reset(self, message, args=None):
		self._check_perms(message.author, 1)
		if not args:
			for q in self.queues:
				await q.reset()
		elif q := find(lambda q: q.name.lower() == args.lower(), self.queues):
			await q.reset()
		else:
			raise bot.Exc.NotFoundError(self.gt("Specified queue not found."))
		await self.update_topic(force_announce=True)

	async def _remove_player(self, message, args=None):
		self._check_perms(message.author, 1)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}remove_player __@user__")
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}remove_player __@user__")
		await self.remove_members(member, reason="moderator")

	async def _add_player(self, message, args=""):
		self._check_perms(message.author, 1)
		args = args.split(" ", maxsplit=1)
		if len(args) != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}add_player __queue__ __@user__")
		elif (queue := find(lambda q: q.name.lower() == args[0].lower(), self.queues)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}add_player __queue__ __@user__")
		elif (member := self.get_member(args[1])) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}add_player __queue__ __@user__")

		resp = await queue.add_member(member)
		if resp == bot.Qr.Success:
			await self.update_expire(member)
			await self.update_topic()

	async def subscribe(self, member, args, unsub=False):
		if not args:
			roles = [self.cfg.promotion_role] if self.cfg.promotion_role else []
		else:
			args = args.split(" ")
			roles = (q.cfg.promotion_role for q in self.queues if q.cfg.promotion_role and any(
				(t == q.name.lower() or t in (a["alias"].lower() for a in q.cfg.tables.aliases) for t in args)
			))

		if unsub:
			roles = [r for r in roles if r in member.roles]
			if not len(roles):
				raise bot.Exc.ValueError(self.gt("No changes to apply."))
			await member.remove_roles(*roles, reason="subscribe command")
			await self.success(self.gt("Removed `{count}` roles from you.").format(
				count=len(roles)
			))

		else:
			roles = [r for r in roles if r not in member.roles]
			if not len(roles):
				raise bot.Exc.ValueError(self.gt("No changes to apply."))
			await member.add_roles(*roles, reason="subscribe command")
			await self.success(self.gt("Added `{count}` roles to you.").format(
				count=len(roles)
			))

	async def _subscribe(self, message, args=None):
		await self.subscribe(message.author, args)

	async def _unsubscribe(self, message, args=None):
		await self.subscribe(message.author, args, unsub=True)

	async def _server(self, message, args=""):
		if len(self.queues) == 1:
			q = self.queues[0]
		elif (q := find(lambda q: q.name.lower() == args.lower(), self.queues)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}server __queue__")
		if not q.cfg.server:
			raise bot.Exc.NotFoundError(self.gt("Server for **{queue}** is not set.").format(
				queue=q.name
			))
		await self.success(q.cfg.server, title=self.gt("Server for **{queue}**").format(
			queue=q.name
		))

	async def _stats(self, message, args=None):
		if not args:
			stats = await bot.stats.qc_stats(self.id)
			target = f"#{self.channel.name}"
		elif member := self.get_member(args):
			stats = await bot.stats.user_stats(self.id, member.id)
			target = get_nick(member)
		else:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}stats [__@user__]")

		embed = Embed(
			title=self.gt("Stats for __{target}__").format(target=target),
			colour=Colour(0x50e3c2),
			description=self.gt("**Total matches: {count}**").format(count=stats['total'])
		)
		for q in stats['queues']:
			embed.add_field(name=q['queue_name'], value=str(q['count']), inline=True)

		await self.channel.send(embed=embed)

	async def _top(self, message, args=None):
		args = args.lower().strip() if args else None
		if args in ["day", self.gt("day")]:
			time_gap = int(time.time()) - (60*60*24)
		elif args in ["week", self.gt("week")]:
			time_gap = int(time.time()) - (60*60*24*7)
		elif args in ["month", self.gt("month")]:
			time_gap = int(time.time()) - (60*60*24*30)
		elif args in ["year", self.gt("year")]:
			time_gap = int(time.time()) - (60*60*24*365)
		elif args:
			raise bot.Exc.SyntaxError("Usage: {prefix}top [{options}]".format(
				prefix=self.cfg.prefix,
				options=" / ".join((self.gt(i) for i in ('day', 'week', 'month', 'year')))
			))
		else:
			time_gap = None

		top = await bot.stats.top(self.id, time_gap=time_gap)
		embed = Embed(
			title=self.gt("Top 10 players for __{target}__").format(target=f"#{self.channel.name}"),
			colour=Colour(0x50e3c2),
			description=self.gt("**Total matches: {count}**").format(count=top['total'])
		)
		for p in top['players']:
			embed.add_field(name=p['nick'], value=str(p['count']), inline=True)
		await self.channel.send(embed=embed)

	async def _cointoss(self, message, args=None):
		if not args or args.lower() in ["heads", self.gt("heads")]:
			pick = 0
		elif args.lower() in ["tails", self.gt("tails")]:
			pick = 1
		else:
			raise bot.Exc.SyntaxError("Usage: {prefix}ct [{options}]".format(
				prefix=self.cfg.prefix,
				options=" / ".join((self.gt(i) for i in ('heads', 'tails')))
			))

		result = randint(0, 1)
		if pick == result:
			await self.channel.send(self.gt("{member} won, its **{side}**!").format(
				member=message.author.mention, side=self.gt(["heads", "tails"][result])
			))
		else:
			await self.channel.send(self.gt("{member} lost, its **{side}**!").format(
				member=message.author.mention, side=self.gt(["heads", "tails"][result])
			))

	async def _help(self, message, args=None):
		if args is None:
			if self.cfg.description:
				await self.channel.send(self.cfg.description)
		elif queue := find(lambda q: q.name.lower() == args.lower(), self.queues):
			if queue.cfg.description:
				await self.channel.send(queue.cfg.description)

	async def maps(self, message, args="", random=False):
		if len(self.queues) == 1:
			q = self.queues[0]
		elif (q := find(lambda q: q.name.lower() == args.lower(), self.queues)) is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}map(s) __queue__")
		if not len(q.cfg.tables.maps):
			raise bot.Exc.NotFoundError(self.gt("No maps is set for **{queue}**.").format(
				queue=q.name
			))

		if random:
			await self.success(f"`{choice(q.cfg.tables.maps)['name']}`")
		else:
			await self.success(
				", ".join((f"`{i['name']}`" for i in q.cfg.tables.maps)),
				title=self.gt("Maps for **{queue}**").format(queue=q.name)
			)

	async def _maps(self, *args, **kwargs):
		await self.maps(*args, **kwargs, random=False)

	async def _map(self, *args, **kwagrs):
		await self.maps(*args, **kwagrs, random=True)

	async def _noadds(self, message, args=None):
		noadds = await bot.noadds.get_noadds(self)
		now = int(time.time())
		s = "```markdown\n"
		s += self.gt(" ID | Prisoner | Left | Reason")
		s += "\n----------------------------------------\n"
		if len(noadds):
			s += "\n".join((
				f" {i['id']} | {i['name']} | {seconds_to_str(max(0,(i['at']+i['duration'])-now))} | {i['reason'] or '-'}"
				for i in noadds
			))
		else:
			s += self.gt("Noadds are empty.")
		await self.channel.send(s+"\n```")

	async def _noadd(self, message, args=""):
		self._check_perms(message.author, 1)
		if len(args := args.split(" ", maxsplit=2)) < 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}noadd __@user__ __duration__ [__reason__]")
		elif (member := self.get_member(args.pop(0))) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))

		try:
			secs = parse_duration(args.pop(0))
		except ValueError:
			raise bot.Exc.SyntaxError(self.gt("Invalid duration format. Syntax: 3h2m1s or 03:02:01."))

		if secs > 60*60*24*30*12*16:
			raise bot.Exc.ValueError(self.gt("Specified duration time is too long."))

		reason = args.pop(0) if len(args) else None
		await bot.noadds.noadd(self, member, secs, message.author, reason=reason)
		await self.success(self.gt("Banned **{member}** for `{duration}`.").format(
			member=get_nick(member),
			duration=seconds_to_str(secs)
		))

	async def _forgive(self, message, args=None):
		self._check_perms(message.author, 1)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}forgive __@user__")
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))

		if await bot.noadds.forgive(self, member, message.author):
			await self.success(self.gt("Done."))
		else:
			raise bot.Exc.NotFoundError(self.gt("Specified member is not banned."))

	async def _phrases_add(self, message, args=""):
		self._check_perms(message.author, 1)
		if len(args := args.split(" ", maxsplit=1)) != 2:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}phrases_add __@user__ __phrase__")
		elif (member := self.get_member(args.pop(0))) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))

		await bot.noadds.phrases_add(self, member, args.pop(0))
		await self.success(self.gt("Done."))

	async def _phrases_clear(self, message, args=None):
		self._check_perms(message.author, 1)
		if args is None:
			member = None
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		await bot.noadds.phrases_clear(self, member=member)
		await self.success(self.gt("Done."))

	async def _set_nick(self, message, args=None):
		if args is None:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}nick __nickname__")
		data = await db.select_one(
			['rating'], 'qc_players',
			where={'channel_id': self.id, 'user_id': message.author.id}
		)
		if not data or data['rating'] is None:
			rating = self.rating.init_rp
		else:
			rating = data['rating']

		await message.author.edit(nick=f"[{rating}] " + args)
