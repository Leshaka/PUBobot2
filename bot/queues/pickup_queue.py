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
				display="Queue size",
				verify=lambda i: 0 < i < 1001
			),
			Variables.BoolVar(
				"is_default",
				display="Default",
				default=1
			),
			Variables.BoolVar(
				"autostart",
				display="Autostart",
				default=1
			),
			Variables.BoolVar(
				"ranked",
				display="Ranked",
				default=0,
				description="Enable ratings feature on this queue."
			),
			Variables.TextVar(
				"start_msg",
				display="Start message",
				verify=lambda s: len(s) < 1001,
				verify_message="Start message is too long."
			),
			Variables.StrVar(
				"server",
				display="Server"
			),
			Variables.OptionVar(
				"pick_captains",
				display="Pick captains",
				options=["by role and rating", "fair pairs", "random", "no captains"],
				default="by role and rating",
				notnull=True
			),
			Variables.OptionVar(
				"pick_teams",
				display="Pick teams",
				options=["draft", "matchmaking", "random teams", "no teams"],
				default="draft",
				notnull=True
			),
			Variables.StrVar(
				"pick_order",
				display="Teams picking order",
				verify=lambda s: set(s) == set("ab"),
				default="abababba",
				verify_message="Pick order can only contain a and b characters.",
				description="a - 1st team picks, b - 2nd team picks, example: ababba"
			),
			Variables.StrVar(
				"team_names",
				display="Team names",
				verify=lambda s: len(s.split()) == 2,
				verify_message="Team names must be exactly two words separated by space.",
				description="Team names separated by space, example: Alpha Beta"
			),
			Variables.StrVar(
				"team_emojis",
				display="Team emojis",
				verify=lambda s: len(s.split()) == 2,
				verify_message="Team emojis must be exactly two emojis separated by space.",
				description="Team emojis separated by space."
			),
			Variables.DurationVar(
				"check_in_timeout",
				display="Require check-in",
				verify=lambda i: 0 < i < 3601,
				verify_message="Check in timeout must be less than a hour.",
				description="Set the check-in stage duration."
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
			),
			Variables.RoleVar(
				"blacklist_role",
				display="Blacklist role"
			),
			Variables.RoleVar(
				"whitelist_role",
				display="Whitelist role"
			),
			Variables.BoolVar(
				"autostart",
				display="Start when the queue is full.",
				default=1
			),
			Variables.IntVar(
				"map_count",
				display="Map count",
				default=1
			)
		],
		tables=[
			VariableTable(
				"aliases", display="Aliases",
				variables=[
					Variables.StrVar("alias", notnull=True)
				]
			),
			VariableTable(
				"maps", display="Maps",
				variables=[
					Variables.StrVar("name", notnull=True)
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
		await cfg.update({"name": name, "size": str(size)})
		return cls(qc, cfg)

	def serialize(self):
		return dict(
			queue_id=self.id,
			channel_id=self.qc.channel.id,
			players=[i.id for i in self.queue]
		)

	async def from_json(self, data):
		players = [self.qc.channel.guild.get_member(user_id) for user_id in data['players']]
		if None in players:
			await self.qc.error(f"Unable to load queue **{self.cfg.name}**, error fetching guild members.")
			return
		self.queue = players
		if self.length:
			bot.active_queues.append(self)

	def __init__(self, qc, cfg):
		self.qc = qc
		self.cfg = cfg
		self.id = self.cfg.p_key
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

	@property
	def length(self):
		return len(self.queue)

	@property
	def promote(self):
		return self.qc.gt("{role}Please add to **{name}** pickup, `{num}` players left!".format(
			role=self.cfg.promotion_role.mention + " " if self.cfg.promotion_role else "",
			name=self.name,
			num=self.cfg.size-self.length
		))

	async def reset(self):
		self.queue = []
		if self in bot.active_queues:
			bot.active_queues.remove(self)

	async def add_member(self, member):
		if member not in self.queue:
			self.queue.append(member)

			if self not in bot.active_queues:
				bot.active_queues.append(self)

			if len(self.queue) == self.cfg.size and self.cfg.autostart:
				await self.start()
				return True

		return False

	async def remove_member(self, member):
		if member in self.queue:
			self.queue.remove(member)
			if not self.length:
				bot.active_queues.remove(self)
		else:
			raise ValueError("Specified Member is not added to the queue.")

	async def start(self):
		if len(self.queue) < 2:
			raise bot.Exc.PubobotException(self.qc.gt("Not enough players to start the queue."))

		await bot.Match.new(
			self, self.qc, list(self.queue),
			team_names=self.cfg.team_names, team_emojis=self.cfg.team_emojis, ranked=self.cfg.ranked,
			team_size=int(self.cfg.size/2), pick_captains=self.cfg.pick_captains,
			captains_role_id=self.cfg.captains_role.id if self.cfg.captains_role else None,
			pick_teams=self.cfg.pick_teams, pick_order=self.cfg.pick_order,
			maps=[i['name'] for i in self.cfg.tables.maps],
			map_count=self.cfg.map_count, check_in_timeout=self.cfg.check_in_timeout,
			start_msg=self.cfg.start_msg, server=self.cfg.server
		)
		players = list(self.queue)
		await self.qc.queue_started(
			members=players,
			message=self.qc.gt("**{queue}** pickup has started @ {channel}!").format(
				queue=self.name,
				channel=self.qc.channel.mention
			)
		)
		await bot.remove_players(*players, reason="pickup started")

	async def revert(self, not_ready, ready):
		old_players = list(self.queue)
		self.queue = list(ready)
		while len(self.queue) < self.cfg.size and len(old_players):
			self.queue.append(old_players.pop(0))
		if len(self.queue) == self.cfg.size:
			await self.start()
			self.queue = list(old_players)
		await self.qc.update_topic(force_announce=True)

		if self not in bot.active_queues and self.length:
			bot.active_queues.append(self)
