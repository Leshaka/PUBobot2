# -*- coding: utf-8 -*-
from discord import Forbidden

from core.console import log
from core.cfg_factory import CfgFactory, Variables, VariableTable
from core.utils import get_nick

import bot


class PickupQueue:

	cfg_factory = CfgFactory(
		"pq_configs",
		p_key="pq_id",
		f_key="channel_id",
		icon="pq.png",
		sections=["General", "Teams", "Appearance"],
		variables=[
			Variables.StrVar(
				"name",
				display="Queue name",
				section="General",
				notnull=True,
				verify=lambda name: len(name) and not any((c in name for c in "+-: \t\n")),
				verify_message="Invalid queue name. A queue name should be one word without +-: characters."
			),
			Variables.TextVar(
				"description",
				display="Description",
				section="Appearance",
				description="Set an answer on '!help queue' command."
			),
			Variables.IntVar(
				"size",
				display="Queue size",
				section="General",
				verify=lambda i: 0 < i < 1001,
				notnull=True
			),
			Variables.BoolVar(
				"is_default",
				display="is default",
				section="General",
				default=1,
				description="Set if users can add to this queue without specifying its name.",
				notnull=True
			),
			Variables.BoolVar(
				"ranked",
				display="is ranked",
				section="General",
				default=0,
				description="Enable rating features on this queue.",
				notnull=True
			),
			Variables.BoolVar(
				"autostart",
				display="Start when full",
				section="General",
				default=1,
				notnull=True
			),
			Variables.DurationVar(
				"check_in_timeout",
				display="Require check-in",
				section="General",
				verify=lambda i: 0 < i < 3601,
				default=60*5,
				verify_message="Check in timeout must be less than a hour.",
				description="Set the check-in stage duration."
			),
			Variables.OptionVar(
				"pick_teams",
				display="Pick teams",
				section="Teams",
				options=["draft", "matchmaking", "random teams", "no teams"],
				default="draft",
				description="\n".join([
					"Set how teams should be picked:",
					"  draft - host a draft stage where captains will have to pick players",
					"  matchmaking - form teams automatically based on players ratings",
					"  random teams - form teams randomly",
					"  no teams - do not form teams, only print the players list"
				]),
				notnull=True
			),
			Variables.OptionVar(
				"pick_captains",
				display="Pick captains",
				section="Teams",
				options=["by role and rating", "fair pairs", "random", "no captains"],
				default="by role and rating",
				description="\n".join([
					"Set how captains should be picked (for 'draft' or 'no teams' above):",
					"  by role and rating - sort by captain role and rating and pick the best",
					"  fair pairs - pick random pair of players with closest ratings to each other",
					"  random - pick captains randomly",
					"  no captains - do not pick captains automatically"
				]),
				notnull=True
			),
			Variables.StrVar(
				"pick_order",
				display="Teams picking order",
				section="Teams",
				verify=lambda s: set(s) == set("ab"),
				default="abababba",
				verify_message="Pick order can only contain a and b characters.",
				description="a - 1st team picks, b - 2nd team picks, example: ababba"
			),
			Variables.StrVar(
				"team_names",
				display="Team names",
				section="Teams",
				verify=lambda s: len(s.split()) == 2,
				verify_message="Team names must be exactly two words separated by space.",
				description="Team names separated by space, example: Alpha Beta"
			),
			Variables.StrVar(
				"team_emojis",
				display="Team emojis",
				section="Teams",
				verify=lambda s: len(s.split()) == 2,
				verify_message="Team emojis must be exactly two emojis separated by space.",
				description="Team emojis separated by space."
			),
			Variables.TextVar(
				"start_msg",
				display="Start message",
				section="Appearance",
				verify=lambda s: len(s) < 1001,
				description="Set additional information to be printed on a match start.",
				verify_message="Start message is too long."
			),
			Variables.TextVar(
				"start_direct_msg",
				display="Start direct message",
				section="Appearance",
				verify=lambda s: len(s) < 1001,
				description="\n".join([
					"Set the content of a direct message sent to players when the queue starts.",
					"You can use this aliases in text: {queue}, {channel}, {server}.",
					"If not set, default translated message is used."
				]),
				verify_message="Start direct message is too long."
			),
			Variables.StrVar(
				"server",
				display="Server",
				section="Appearance",
				description="Print this server on a match start.",
				verify=lambda s: len(s) < 101,
				verify_message="Server string is too long."
			),
			Variables.RoleVar(
				"promotion_role",
				display="Promotion role",
				section="General",
				description="Set a role to highlight on !promote and !sub commands."
			),
			Variables.TextVar(
				"promotion_msg",
				display="Promotion message",
				section="Appearance",
				description="Replace default promotion message. You can use {name}, {role} and {left} placeholders in the text."
			),
			Variables.RoleVar(
				"captains_role",
				display="Captains role",
				section="Teams",
				description="Users with this role may have preference in captains choosing process."
			),
			Variables.RoleVar(
				"blacklist_role",
				display="Blacklist role",
				section="General",
				description="Users with this role wont be able to add to this queue."
			),
			Variables.RoleVar(
				"whitelist_role",
				display="Whitelist role",
				section="General",
				description="Only users with this role will be able to add to this queue."
			),
			Variables.IntVar(
				"map_count",
				display="Map count",
				section="Appearance",
				default=1,
				verify=lambda n: 0 <= n <= 5,
				verify_message="Maps number must be between 0 and 5.",
				description="Number of maps to show on match start."
			),
			Variables.IntVar(
				"vote_maps",
				display="Vote poll map count",
				section="Appearance",
				default=None,
				verify=lambda n: 2 <= n <= 5,
				verify_message="Vote maps number must be between 2 and 5.",
				description="Set to enable map voting, this requires check-in timeout to be set."
			)
		],
		tables=[
			VariableTable(
				"aliases", display="Aliases", section="General",
				description="Other names for this queue, you can also group queues by giving them a same alias.",
				variables=[
					Variables.StrVar("alias", notnull=True)
				]
			),
			VariableTable(
				"maps", display="Maps", section="Appearance",
				description="List of maps to choose from.",
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
		self.last_map = None

	@property
	def name(self):
		return self.cfg.name

	@property
	def status(self):  # (length/max)
		return f"{len(self.queue)}/{self.cfg.size}"

	@property
	def who(self):
		return "/".join([f"`{get_nick(m)}`" for m in self.queue])

	@property
	def length(self):
		return len(self.queue)

	async def promote(self):
		promotion_role = self.cfg.promotion_role or self.qc.cfg.promotion_role
		promotion_msg = self.cfg.promotion_msg or self.qc.gt("{role} Please add to **{name}** pickup, `{left}` players left!")
		promotion_msg = promotion_msg.format(
			role=promotion_role.mention if promotion_role else "",
			name=self.name,
			left=self.cfg.size-self.length
		)

		if promotion_role and not promotion_role.mentionable:
			try:
				await promotion_role.edit(reason="Promote command", mentionable=True)
			except Forbidden:
				raise bot.Exc.PermissionError("Insufficient permissions to set the promotion role mentionable.")
			else:
				await self.qc.channel.send(promotion_msg)
				await promotion_role.edit(reason="Promote command", mentionable=False)
				return
		else:
			await self.qc.channel.send(promotion_msg)

	async def reset(self):
		self.queue = []
		if self in bot.active_queues:
			bot.active_queues.remove(self)

	async def add_member(self, member):
		if (
			self.cfg.blacklist_role and self.cfg.blacklist_role in member.roles
			or self.cfg.whitelist_role and self.cfg.whitelist_role not in member.roles
		):
			return bot.Qr.NotAllowed

		if member not in self.queue:
			self.queue.append(member)

			if self not in bot.active_queues:
				bot.active_queues.append(self)

			if len(self.queue) == self.cfg.size and self.cfg.autostart:
				await self.start()
				return bot.Qr.QueueStarted

			return bot.Qr.Success
		else:
			return bot.Qr.Duplicate

	def is_added(self, member):
		return member in self.queue

	def pop_members(self, *members):
		ids = [m.id for m in members]
		members = [member for member in self.queue if member.id in ids]
		for m in members:
			self.queue.remove(m)
		return members

	async def start(self):
		if len(self.queue) < 2:
			raise bot.Exc.PubobotException(self.qc.gt("Not enough players to start the queue."))

		players = list(self.queue)
		dm_text = self.cfg.start_direct_msg or self.qc.gt("**{queue}** pickup has started @ {channel}!")
		await self.qc.queue_started(
			members=players,
			message=dm_text.format(
				queue=self.name,
				channel=self.qc.channel.mention,
				server=self.cfg.server
			)
		)

		await bot.Match.new(
			self, self.qc, players,
			team_names=self.cfg.team_names.split(" ") if self.cfg.team_names else None,
			team_emojis=self.cfg.team_emojis.split(" ") if self.cfg.team_emojis else None,
			ranked=self.cfg.ranked, team_size=int(self.cfg.size/2), pick_captains=self.cfg.pick_captains,
			captains_role_id=self.cfg.captains_role.id if self.cfg.captains_role else None,
			pick_teams=self.cfg.pick_teams, pick_order=self.cfg.pick_order,
			maps=[i['name'] for i in self.cfg.tables.maps], vote_maps=self.cfg.vote_maps,
			map_count=self.cfg.map_count, check_in_timeout=self.cfg.check_in_timeout,
			start_msg=self.cfg.start_msg, server=self.cfg.server
		)

	async def revert(self, not_ready, ready):
		old_players = list(self.queue)
		self.queue = list(ready)
		while len(self.queue) < self.cfg.size and len(old_players):
			self.queue.append(old_players.pop(0))
		if len(self.queue) == self.cfg.size:
			await self.start()
			self.queue = list(old_players)
		else:
			for p in ready:
				await self.qc.update_expire(p)

		await self.qc.update_topic(force_announce=True)
		if self not in bot.active_queues and self.length:
			bot.active_queues.append(self)
