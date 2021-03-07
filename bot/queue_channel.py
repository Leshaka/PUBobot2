# -*- coding: utf-8 -*-
import re
import json
import time
import asyncio
import traceback
from discord import Embed, Colour, Forbidden

from core.config import cfg
from core.console import log
from core.cfg_factory import CfgFactory, Variables, VariableTable
from core.locales import locales
from core.utils import error_embed, ok_embed, find, get, join_and, seconds_to_str, parse_duration, get_nick
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
		variables=[
			Variables.StrVar(
				"prefix",
				display="Command prefix",
				description="Set the prefix before for the bot`s commands",
				verify=lambda x: len(x) == 1,
				verify_message="Command prefix must be exactly one symbol.",
				default="!",
				notnull=True
			),
			Variables.OptionVar(
				"lang",
				display="Language",
				description="Select bot translation language",
				options=locales.keys(),
				default="en",
				notnull=True,
				on_change=bot.update_qc_lang
			),
			Variables.RoleVar(
				"admin_role",
				display="Admin role",
				description="Members with this role will be able to change the bot`s settings and use moderation commands."
			),
			Variables.RoleVar(
				"moderator_role",
				display="Moderator role",
				description="Members with this role will be able to use the bot`s moderation commands."
			),
			Variables.RoleVar(
				"promotion_role",
				display="Promotion role",
				description="Set a role to highlight on !promote and !sub commands.",
			),
			Variables.DurationVar(
				"promotion_delay",
				display="Promotion delay",
				description="Set time delay between players can promote queues.",
				verify=lambda x: 0 <= MAX_PROMOTION_DELAY,
				verify_message=f"Promotion delay time must be less than {seconds_to_str(MAX_EXPIRE_TIME)}"
			),
			Variables.BoolVar(
				"remove_afk",
				display="Auto remove on AFK status",
				default=1,
				notnull=True
			),
			Variables.BoolVar(
				"remove_offline",
				display="Auto remove on offline status",
				default=1,
				notnull=True
			),
			Variables.DurationVar(
				"expire_time",
				display="Auto remove on timer after last !add command",
				verify=lambda x: 0 < x <= MAX_EXPIRE_TIME,
				verify_message=f"Expire time must be less than {seconds_to_str(MAX_EXPIRE_TIME)}"
			),
			Variables.RoleVar(
				"blacklist_role",
				display="Blacklist role",
				description="Players with this role wont be able to add to queues.",
			),
			Variables.RoleVar(
				"whitelist_role",
				display="Whitelist role",
				description="If set, only players with this role will be able to add to queues."
			),
			Variables.OptionVar(
				"rating_system",
				display="Rating system",
				description="Set player's rating calculation method.",
				options=rating_names.keys(),
				default="TrueSkill",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_initial",
				display="Initial rating",
				description="Set player's initial rating.",
				default=1500,
				verify=lambda x: 0 <= x <= 10000,
				verify_message="Initial rating must be between 0 and 10000",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_deviation",
				display="Rating deviation",
				description="Set initial rating deviation.",
				default=300,
				verify=lambda x: 0 <= x <= 3000,
				verify_message="Rating deviation must be between 0 and 3000",
				notnull=True,
				on_change=bot.update_rating_system
			),
			Variables.IntVar(
				"rating_scale",
				display="Rating scale",
				description="Set rating scale.",
				verify=lambda x: 4 <= x <= 256,
				verify_message="Rating scale must be between 4 and 256",
				notnull=True,
				default=32
			),
			Variables.BoolVar(
				"rating_nicks",
				display="Set ratings to nicks",
				default=0,
				notnull=True
			)
		],
		tables=[
			VariableTable(
				'ranks', display="Rating ranks",
				variables=[
					Variables.StrVar("rank", default="〈E〉"),
					Variables.IntVar("rating", default=1200),
					Variables.RoleVar("role")
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
			channel_id=text_channel.id,
			init_rp=self.cfg.rating_initial,
			init_deviation=self.cfg.rating_deviation,
			scale=self.cfg.rating_scale
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
			capfor=self._cap_for,
			pick=self._pick,
			teams=self._teams,
			put=self._put,
			subme=self._sub_me,
			subfor=self._sub_for,
			rank=self._rank,
			lb=self._leaderboard,
			leaderboard=self._leaderboard,
			rl=self._rl,
			rd=self._rd,
			rw=self._rw,
			expire=self._expire,
			default_expire=self._default_expire,
			ao=self._allow_offline,
			allow_offline=self._allow_offline,
			matches=self._matches,
			promote=self._promote,
			rating_set=self._rating_set,
			seed=self._rating_set,
			rating_hide=self._rating_hide,
			rating_unhide=self._rating_unhide,
			rating_reset=self._rating_reset,
			cancel_match=self._cancel_match,
			undo_match=self._undo_match,
			switch_dms=self._switch_dms,
			start=self._start,
			stats_reset=self._stats_reset,
			stats_reset_player=self._stats_reset_player
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
			channel_id=self.channel.id,
			init_rp=self.cfg.rating_initial,
			init_deviation=self.cfg.rating_deviation,
			scale=self.cfg.rating_scale
		)

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

	async def new_queue(self, name, size, kind):
		kind.validate_name(name)
		if 1 > size > 100:
			raise ValueError("Queue size must be between 2 and 100.")
		if name.lower() in [i.name.lower() for i in self.queues]:
			raise ValueError("Queue with this name already exists.")

		q_obj = await kind.create(self, name, size)
		self.queues.append(q_obj)
		return q_obj

	async def update_topic(self, force_announce=False):
		populated = [q for q in self.queues if len(q.queue)]
		if not len(populated):
			new_topic = f"> {self.gt('no players')}"
		elif len(populated) < 5:
			new_topic = "\n".join([f"> **{q.name}** ({q.status}) | {q.who}" for q in populated])
		else:
			new_topic = "> [" + " | ".join([f"**{q.name}** ({q.status})" for q in populated]) + "]"
		if new_topic != self.topic or force_announce:
			self.topic = new_topic
			await self.channel.send(self.topic)

	async def auto_remove(self, member):
		if bot.expire.get(self, member) is None:
			if str(member.status) == "idle" and self.cfg.remove_afk:
				await self.remove_members(member, reason="afk")
			elif str(member.status) == "offline" and self.cfg.remove_offline:
				await self.remove_members(member, reason="offline")

	async def remove_members(self, *members, reason=None):
		affected = set()
		for q in (q for q in self.queues if q.length):
			for m in members:
				try:
					await q.remove_member(m)
					affected.add(m)
				except ValueError:
					pass

		if len(affected):
			await self.update_topic()
			if reason:
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
		print(string)
		if highlight := re.match(r"<@!?(\d+)>", string):
			print(highlight.group(1))
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
		below = sorted(
			(rank for rank in self.cfg.tables.ranks if rank['rating'] < rating),
			key=lambda r: r['rating'], reverse=True
		)
		if not len(below):
			return {'rank': '〈?〉', 'rating': 0, 'role': None}
		return below[0]

	async def update_rating_roles(self, *members):
		asyncio.create_task(self._update_rating_roles(*members))

	async def _update_rating_roles(self, *members):
		data = await self.rating.get_players((i.id for i in members))
		roles = {i['user_id']: self.rating_rank(i['rating'])['role'] for i in data}
		ratings = {i['user_id']: i['rating'] for i in data}
		all_roles = [i['role'] for i in self.cfg.tables.ranks if i is not None]

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

		for m in members:
			bot.expire.cancel(self, m)
		if message:
			asyncio.create_task(self._dm_members(members, message))

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
			f, args = self.commands.get(cmd[1:]), message.content.split(' ', 1)[1:]
		else:
			return

		if f:
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

	async def _add_member(self, message, args=None):
		if self.cfg.blacklist_role and self.cfg.blacklist_role in message.author.roles:
			raise bot.Exc.PermissionError(self.gt("You are not allowed to add to queues."))
		if self.cfg.whitelist_role and self.cfg.whitelist_role not in message.author.roles:
			raise bot.Exc.PermissionError(self.gt("You are not allowed to add to queues."))

		if any((message.author in m.players for m in bot.active_matches)):
			raise bot.Exc.InMatchError(self.gt("You are already in an active match."))

		targets = args.lower().split(" ") if args else []

		# select the only one queue on the channel
		if not len(targets) and len(self.queues) == 1:
			t_queues = self.queues

		# select queues requested by user
		elif len(targets):
			t_queues = (q for q in self.queues if any(
				(t == q.name.lower() or t in (a["alias"] for a in q.cfg.tables.aliases) for t in targets)
			))

		# select active queues or default queues if no active queues
		else:
			t_queues = [q for q in self.queues if len(q.queue)]
			if not len(t_queues):
				t_queues = (q for q in self.queues if q.cfg.is_default)

		is_started = False
		for q in t_queues:
			if is_started := await q.add_member(message.author):
				break
		if not is_started:
			personal_expire = await db.select_one(['expire'], 'players', where={'user_id': message.author.id})
			personal_expire = personal_expire.get('expire') if personal_expire else None
			if personal_expire not in [0, None]:
				bot.expire.set(self, message.author, personal_expire)
			elif self.cfg.expire_time and personal_expire is None:
				bot.expire.set(self, message.author, self.cfg.expire_time)

		await self.update_topic()

	async def _remove_member(self, message, args=None):
		targets = args.lower().split(" ") if args else []

		t_queues = (q for q in self.queues if len(q.queue))
		if len(targets):
			t_queues = (q for q in self.queues if any(
				(t == q.name or t in (a["alias"] for a in q.cfg.tables.aliases) for t in targets)
			))
		for q in t_queues:
			try:
				await q.remove_member(message.author)
			except ValueError:  # member is not added to the queue
				pass
		await self.update_topic()

	async def _who(self, message, args=None):
		targets = args.lower().split(" ") if args else []

		if len(targets):
			t_queues = (q for q in self.queues if any(
				(t == q.name or t in (a["alias"] for a in q.cfg.tables.aliases) for t in targets)
			))
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
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		await match.draft.pick(message.author, member)

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
		if self.get_match(message.author) is not None:
			raise bot.Exc.InMatchError(self.gt("You are already in an active match"))
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}sub_for __player__")
		elif (member := self.get_member(args)) is None:
			raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		elif (match := self.get_match(member)) is None:
			raise bot.Exc.NotInMatchError(self.gt("Specified user is not in a match."))
		await match.draft.sub_for(message.author, member)

	async def _rank(self, message, args=None):
		if args:
			if (member := self.get_member(args)) is None:
				raise bot.Exc.SyntaxError(self.gt("Specified user not found."))
		else:
			member = message.author

		data = await db.select(
			['user_id', 'rating', 'deviation', 'channel_id', 'wins', 'losses', 'draws'], "qc_players",
			where={'channel_id': self.channel.id}, order_by="rating"
		)
		if p := find(lambda i: i['user_id'] == member.id, data):
			embed = Embed(title=f"__{get_nick(member)}__", colour=Colour(0x7289DA))
			embed.add_field(name="№", value=f"**{data.index(p)+1}**", inline=True)
			embed.add_field(name="Matches", value=f"**{(p['wins']+p['losses']+p['draws'])}**", inline=True)
			if p['rating']:
				embed.add_field(name="Rank", value=f"**{self.rating_rank(p['rating'])['rank']}**", inline=True)
				embed.add_field(name="Rating", value=f"**{p['rating']}**±{p['deviation']}")
			else:
				embed.add_field(name="Rank", value="**〈?〉**", inline=True)
				embed.add_field(name="Rating", value="**?**")
			embed.add_field(name="W/L/D", value=f"**{p['wins']}**/**{p['losses']}**/**{p['draws']}**", inline=True)
			embed.add_field(name="Winrate", value="**{}%**\n\u200b".format(
				int(p['wins']*100 / (p['wins']+p['losses'] or 1))
			), inline=True)
			if member.avatar_url:
				embed.set_thumbnail(url=member.avatar_url)

			changes = await db.select(
				('at', 'rating_change', 'match_id', 'reason'),
				'qc_rating_history', where=dict(user_id=member.id, channel_id=self.channel.id),
				order_by='id', limit=3
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
		await match.report_loss(message.author, draw=False)

	async def _rd(self, message, args=None):
		if (match := self.get_match(message.author)) is None:
			raise bot.Exc.NotInMatchError(self.gt("You are not in an active match."))
		await match.report_loss(message.author, draw=True)

	async def _rw(self, message, args=[]):
		self._check_perms(message.author, 1)
		args = args.split(" ", maxsplit=1)
		if len(args) != 2 or not args[0].isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rw __match_id__ __team_name__ or draw")
		if (match := find(lambda m: m.qc == self and m.id == int(args[0]), bot.active_matches)) is None:
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.").format(
				prefix=self.cfg.prefix
			))
		await match.report_win(args[1])

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
			await self.success(self.gt("Your allow offline immune is gone."))
		else:
			bot.allow_offline.append(message.author.id)
			await self.success(self.gt("You now have the allow offline immune."))

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

		data = await db.select(
			['nick', 'rating', 'deviation', 'wins', 'losses', 'draws'], 'qc_players',
			where={'channel_id': self.channel.id, 'is_hidden': 0}, order_by="rating"
		)
		data = [i for i in data if i['rating'] is not None][page*10:(page+1)*10]

		if len(data):
			lines = ["{0:^3}|{1:^11}|{2:^25.25}|{3:^9}| {4}".format(
				(page*10)+(n+1),
				str(data[n]['rating']) + self.rating_rank(data[n]['rating'])['rank'],
				data[n]['nick'],
				int(data[n]['wins']+data[n]['losses']+data[n]['draws']),
				"{0}/{1}/{2} ({3}%)".format(
					data[n]['wins'],
					data[n]['losses'],
					data[n]['draws'],
					int(data[n]['wins']*100/((data[n]['wins']+data[n]['losses']) or 1))
				)
			) for n in range(len(data))]

			text = "```markdown\n № | Rating〈Ξ〉 |         Nickname        | Matches |  W/L/D\n{0}\n{1}```".format(
				"-"*60,
				"\n".join(lines)
			)
			await self.channel.send(text)
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
			raise bot.Exc.PermissionError(self.gt("You promote to fast, `{delay}` until next promote.".format(
				delay=seconds_to_str((self.cfg.promotion_delay+self.last_promote)-now)
			)))

		await self.channel.send(queue.promote)
		self.last_promote = now

	async def _rating_set(self, message, args=None):
		self._check_perms(message.author, 1)
		args = args.split(" ")
		try:
			if (member := self.get_member(args.pop(0))) is None:
				raise ValueError()
			rating = int(args.pop(0))
			deviation = int(args.pop(0)) if len(args) else None
		except (ValueError, IndexError):
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}rating_set __@user__ __rating__ [__deviation__]")

		if not 0 < rating < 10000 or not 0 < (deviation or 1) < 3000:
			raise bot.Exc.ValueError("Bad rating or deviation value.")

		await self.rating.set_rating(member, rating, deviation)
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

	async def _cancel_match(self, message, args=""):
		self._check_perms(message.author, 1)
		if not args.isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}cancel_match __match_id__")

		if not (match := get(bot.active_matches, id=int(args))):
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.".format(
				prefix=self.cfg.prefix
			)))

		await match.cancel()

	async def _undo_match(self, message, args=""):
		self._check_perms(message.author, 1)
		if not args.isdigit():
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}undo_match __match_id__")

		result = await bot.stats.undo_match(int(args), self)
		if result:
			await self.success(self.gt("Done."))
		else:
			raise bot.Exc.NotFoundError(self.gt("Could not find match with specified id. Check `{prefix}matches`.".format(
				prefix=self.cfg.prefix
			)))

	async def _switch_dms(self, message, args=""):
		data = await db.select_one(('allow_dm', ), 'players', where={'user_id': message.author.id})
		if data:
			allow_dm = 1 if data['allow_dm'] == 0 else 0
			await db.update('players', {'allow_dm': allow_dm}, keys={'user_id': message.author.id})
		else:
			allow_dm = 0
			await db.insert('players', {'allow_dm': allow_dm, 'user_id': message.author.id})

		if allow_dm:
			await self.success(self.gt("Your DM notifications is now turned off."), reply_to=message.author)
		else:
			await self.success(self.gt("Your DM notifications is now turned on."), reply_to=message.author)

	async def _start(self, message, args=None):
		self._check_perms(message.author, 1)
		if not args:
			raise bot.Exc.SyntaxError(f"Usage: {self.cfg.prefix}start __queue__")
		if (queue := get(self.queues, name=args)) is None:
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
