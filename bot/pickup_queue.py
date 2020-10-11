# -*- coding: utf-8 -*-
from core.console import log
from core.cfg_factory import CfgFactory, Variables


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
				"ranked",
				display="Ranked",
				default=0,
				description="Enable ratings feature on this queue."
			),
			Variables.RoleVar(
				"promotion_role",
				display="Promotion role",
				description="Set a role to highlight on !promote and !sub commands."
			)
		]
	)

	@staticmethod
	def validate_name(name):
		if not len(name) or any((c in name for c in "+-: \t\n")):
			raise ValueError(f"Invalid queue name '{name}'. Queue name should be one word without +-: characters.")
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

	def who(self):
		return "[{} ({}/{})] {}".format(
			self.name,
			len(self.queue),
			self.cfg.size,
			"/".join("`{}`".format(m.nick or m.name) for m in self.queue)
		)

	def add(self, member):
		self.queue.add(member)

	def remove(self, member):
		self.queue.remove(member)