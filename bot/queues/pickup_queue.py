# -*- coding: utf-8 -*-
from core.console import log
from core.cfg_factory import CfgFactory, Variables, VariableTable

import bot


class PickupQueue:

	cfg_factory = CfgFactory(
		"pq_configs",
		p_key="pq_id",
		f_key="channel_id",
		variables=[
			Variables.StrVar(
				"name",
				display="Queue name"
			),
			Variables.IntVar(
				"size",
				display="Queue size"
			),
			Variables.BoolVar(
				"is_default",
				display="Default",
				default=1
			),
			Variables.BoolVar(
				"ranked",
				display="Ranked",
				default=0,
				description="Enable ratings feature on this queue."
			),
			Variables.RoleVar(
				"promotion_role",
				display="Promotion role",
				description="Set a role to highlight on !promote and !sub commands."
			),
			Variables.RoleVar(
				"captains_role",
				display="Captains role",
				description="Users with this role may have preference in captains choosing process."
			)
		],
		tables=[
			VariableTable(
				"aliases", display="Aliases",
				variables=[
					Variables.StrVar("alias", notnull=True)
				]
			)
		]
	)

	@staticmethod
	def validate_name(name):
		if not len(name) or any((c in name for c in "+-: \t\n")):
			raise ValueError(f"Invalid queue name '{name}'. A queue name should be one word without +-: characters.")
		return name

	@classmethod
	async def create(cls, qc, name, size=2):
		cfg = await cls.cfg_factory.spawn(qc.channel.guild, f_key=qc.channel.id)
		await cfg.update({"name": name, "size": size})
		return cls(qc, cfg)

	def __init__(self, qc, cfg):
		self.qc = qc
		self.cfg = cfg
		self.queue = []

	@property
	def name(self):
		return self.cfg.name

	@property
	def status(self):  # (length/max)
		return f"{len(self.queue)}/{self.cfg.size}"

	@property
	def who(self):
		return "/".join([f"`{m.nick or m.name}`" for m in self.queue])

	async def add_member(self, member):
		if member not in self.queue:
			self.queue.append(member)
			if len(self.queue) == self.cfg.size:
				await self.start()
				return True
		return False

	async def remove_member(self, member):
		if member in self.queue:
			self.queue.remove(member)
		else:
			raise ValueError("Specified Member is not added to the queue.")

	async def start(self):
		bot.Match(self, self.qc, list(self.queue), check_in_timeout=None, pick_teams="random teams", ranked=True)
		await self.qc.remove_members(list(self.queue))

	async def revert(self, not_ready, ready):
		old_players = list(self.queue)
		self.queue = list(ready)
		while len(self.queue) < self.cfg.size and len(old_players):
			self.queue.append(old_players.pop(0))
		if len(self.queue) == self.cfg.size:
			await self.start()
			self.queue = list(old_players)
		await self.qc.update_topic(force_announce=True)
