# -*- coding: utf-8 -*-
from core.utils import find


class Draft:

	pick_steps = {
		"a": 0,
		"b": 1
	}

	def __init__(self, match, pick_order, captains_role_id):
		self.m = match
		self.pick_order = [self.pick_steps[i] for i in pick_order] if pick_order else []
		self.captains_role_id = captains_role_id
		self.sub_queue = []

		if self.m.pick_teams == "draft":
			self.m.states.append(self.m.DRAFT)

	async def start(self):
		if not len(self.m.teams[2]):
			await self.m.next_state()
			return

		await self.m.send(
			"__" + self.m.gt("{queue} is now on the draft stage!").format(queue=f"**{self.m.queue.name}**") + "__"
		)
		await self.print()

	async def print(self):
		teams_s = []
		for team in self.m.teams[:2]:
			teams_s.append("> {emoji} ❲{team}❳{rating}".format(
				emoji=team.emoji,
				team=" + ".join(
					[f"`{self.m.rank_str(p)}{p.nick or p.name}`" for p in team]
				) if len(team) else f"`{team.name}`",
				rating=f" 〈__{sum([self.m.ratings[p.id] for p in team])}__〉" if self.m.ranked else ""
			))
		content = f"\n>          :fire: **{self.m.gt('VERSUS')}** :fire:\n".join(teams_s)
		content += "\n\n " + f"__{self.m.gt('Unpicked')}__:\n"
		content += "\n".join([f"  - `{self.m.rank_str(m)}{m.nick or m.name}`" for m in self.m.teams[2]])

		if len(self.m.teams[0]) and len(self.m.teams[1]):
			pick_step = len(self.m.teams[0]) + len(self.m.teams[1]) - 2
			picker_team = self.m.teams[self.pick_order[pick_step]] if pick_step < len(self.pick_order)-1 else None
			if picker_team:
				content += "\n\n> " + self.m.gt("{member}'s turn to pick!").format(member=f"<@{picker_team[0].id}>")
		else:
			content += "\n\n> " + self.m.gt(
				"Type {cmd} to become a captain and start picking teams."
			).format(cmd=f"`{self.m.qc.cfg.prefix}capfor {'/'.join((team.name.lower() for team in self.m.teams))}`")

		await self.m.send(content)

	async def refresh(self):
		if len(self.m.teams[2]) or self.m.state != self.m.DRAFT:
			await self.print()
		else:
			await self.m.next_state()

	async def cap_for(self, author, team_name):
		if self.m.state != self.m.DRAFT:
			await self.m.error(self.m.gt("The match is not on the draft stage."))
		elif self.captains_role_id and self.captains_role_id not in (r.id for r in author.roles):
			await self.m.error(self.m.gt("You must possess the captain's role."))
		elif (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams[:2])) is None:
			await self.m.error(self.m.gt("Team with name '{name}' not found.".format(name=team_name)))
		elif len(team):
			await self.m.error(self.m.gt("Team {name} already have a captain.".format(name=f"**{team.name}**")))
		else:
			find(lambda t: author in t, self.m.teams).remove(author)
			team.append(author)
			await self.print()

	async def pick(self, author, player):
		pick_step = max(0, (len(self.m.teams[0]) + len(self.m.teams[1]) - 2))
		picker_team = self.m.teams[self.pick_order[pick_step]] if pick_step < len(self.pick_order) - 1 else None

		if self.m.state != self.m.DRAFT:
			await self.m.error(self.m.gt("The match is not on the draft stage."))
		elif (team := find(lambda t: author in t[:1], self.m.teams[:2])) is None:
			await self.m.error(self.m.gt("You are not a captain."))
		elif picker_team is not None and picker_team is not team:
			await self.m.error(self.m.gt("Not your turn to pick."))
		elif player not in self.m.teams[2]:
			await self.m.error(self.m.gt("Specified player not in the unpicked list."))
		else:
			self.m.teams[2].remove(player)
			team.append(player)
			await self.refresh()

	async def put(self, player, team_name):
		if (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams)) is None:
			await self.m.error(self.m.gt("Team with name '{name}' not found."))
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			await self.m.error(self.m.gt("The match must be on the draft or waiting report stage."))
		else:
			find(lambda t: player in t, self.m.teams).remove(player)
			team.append(player)
			await self.refresh()

	async def sub_me(self, author):
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			await self.m.error(self.m.gt("The match must be on the draft or waiting report stage."))
		elif author not in self.sub_queue:
			self.sub_queue.append(author)

	async def sub_for(self, author, player):
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			await self.m.error(self.m.gt("The match must be on the draft or waiting report stage."))
		elif player not in self.sub_queue:
			await self.m.error(self.m.gt("Specified player is not looking for a substitute."))
		else:
			team = find(lambda t: player in t, self.teams)
			team[team.index(player)] = author
			self.m.players.remove(player)
			self.m.players.append(author)
			self.sub_queue.remove(player)
			await self.print()