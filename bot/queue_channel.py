# -*- coding: utf-8 -*-
import re

from core.config import cfg
from core.console import log
from core.cfg_factory import CfgFactory, Variables, VariableTable
from core.locales import locales
from core.utils import error_embed, ok_embed, get

import bot


class QueueChannel:

	cfg_factory = CfgFactory(
		"qc_configs",
		p_key="channel_id",
		variables=[
			Variables.RoleVar(
				"admin_role",
				display="Admin role",
				description="Members with this role will be able to use the bot`s settings and use moderation commands."
			),
			Variables.RoleVar(
				"moderator_role",
				display="Moderator role",
				description="Members with this role will be able to use the bot`s moderation commands."
			),
			Variables.StrVar(
				"prefix",
				display="Command prefix",
				description="Set the prefix before all bot`s commands",
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
				"promotion_role",
				display="Promotion role",
				description="Set a role to highlight on !promote and !sub commands.",
			),
			Variables.IntVar(
				"promotion_delay",
				display="Promotion delay",
				description="Set a cooldown time between !promote and !sub commands can be used."
			),
			Variables.BoolVar(
				"rating_calibrate",
				display="Rating calibration boost",
				description="Set to enable rating boost on first 10 user's matches."
			),
			Variables.IntVar(
				"rating_k",
				display="Rating multiplayer",
				description="Change rating K-factor (gain/loss multiplayer)."
			),
			Variables.BoolVar(
				"rating_streaks",
				display="Rating streak boost",
				description="Enable rating streaks (from x1.5 for (3 wins/loses in a row) to x3.0 (6+ wins/loses in a row))."
			)
		],
		tables=[
			VariableTable(
				'ranks', display="Rating ranks",
				variables=[
					Variables.StrVar("rank", default="〈E〉"),
					Variables.IntVar("rating", default=1200),
					Variables.RoleVar("role")
				]
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
		self._ = locales[self.cfg.lang]
		self.queues = []
		self.channel = text_channel
		self.commands = dict(
			add_pickup=self._add_pickup,
			queues=self._show_queues,
			add=self._add_member,
			j=self._add_member,
			remove=self._remove_member,
			l=self._remove_member,
			who=self._who
		)

	def update_lang(self):
		self._ = locales[self.cfg.lang]

	def access_level(self, member):
		if (self.cfg.admin_role in member.roles or
					member.id == cfg.DC_OWNER_ID or
					self.channel.permissions_for(member).administrator):
			return 2
		elif self.cfg.moderator_role in member.roles:
			return 1
		else:
			return 0

	async def new_queue(self, name, size, kind):
		kind.validate_name(name)
		if 1 > size > 100:
			raise ValueError("Queue size must be between 2 and 100.")
		if name.lower() in [i.name.lower() for i in self.queues]:
			raise ValueError("Queue with this name already exists.")

		q_obj = await kind.create(self, name, size)
		self.queues.append(q_obj)
		return q_obj

	async def process_msg(self, message):
		if not len(message.content) > 1:
			return

		cmd = message.content.split(' ', 1)[0].lower()

		# special commands
		if re.match(r"^\+..", cmd):
			await self._add_member(message, message.content[1:])
		elif re.match(r"^-..", cmd):
			await self._remove_member(message, message.content[1:])
		elif cmd == "++":
			await self._add_member(message, "")
		elif cmd == "--":
			await self._add_member(message, "")

		# normal commands starting with prefix
		if self.cfg.prefix != cmd[0]:
			return

		f = self.commands.get(cmd[1:])
		if f:
			await f(message, *message.content.split(' ', 1)[1:])

	#  Bot commands #

	async def _add_pickup(self, message, args=""):
		args = args.lower().split(" ")
		if len(args) != 2 or not args[1].isdigit():
			await self.channel.send(embed=error_embed(f"Usage: {self.cfg.prefix}add_pickups __name__ __size__"))
			return
		try:
			pq = await self.new_queue(args[0], int(args[1]), bot.PickupQueue)
		except ValueError as e:
			await self.channel.send(embed=error_embed(str(e)))
		else:
			await self.channel.send(embed=ok_embed(f"[**{pq.name}** ({pq.status})]"))

	async def _show_queues(self, message, args=None):
		if len(self.queues):
			await self.channel.send("[" + " | ".join(
				[f"**{q.name}** ({q.status})" for q in self.queues]
			) + "]")
		else:
			await self.channel.send("[ **no queues configured** ]")

	async def _add_member(self, message, args=None):
		pass

	async def _remove_member(self, message, args=None):
		pass

	async def _who(self, message, args=None):
		pass
