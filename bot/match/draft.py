# -*- coding: utf-8 -*-
import bot
from core.utils import find
from discord import DiscordException


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

		if self.m.cfg['pick_teams'] == "draft":
			self.m.states.append(self.m.DRAFT)

	async def start(self):
		await self.refresh()

	async def print(self):
		try:
			await self.m.send(embed=self.m.embeds.draft())
		except DiscordException:
			pass


	async def refresh(self):
		if self.m.state != self.m.DRAFT:
			await self.print()
		elif len(self.m.teams[2]) and any((len(t) < self.m.cfg['team_size'] for t in self.m.teams)):
			await self.print()
		else:
			await self.m.next_state()

	async def cap_for(self, author, team_name):
		if self.m.state != self.m.DRAFT:
			raise bot.Exc.MatchStateError(self.m.gt("The match is not on the draft stage."))
		elif self.captains_role_id and self.captains_role_id not in (r.id for r in author.roles):
			raise bot.Exc.PermissionError(self.m.gt("You must possess the captain's role."))
		elif (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams[:2])) is None:
			raise bot.Exc.SyntaxError(self.m.gt("Specified team name not found."))
		elif len(team):
			raise bot.Exc.PermissionError(self.m.gt("Team {name} already have a captain.".format(name=f"**{team.name}**")))
		find(lambda t: author in t, self.m.teams).remove(author)
		team.append(author)
		await self.print()

	async def pick(self, author, player):
		pick_step = max(0, (len(self.m.teams[0]) + len(self.m.teams[1]) - 2))
		picker_team = self.m.teams[self.pick_order[pick_step]] if pick_step < len(self.pick_order) - 1 else None

		if self.m.state != self.m.DRAFT:
			raise bot.Exc.MatchStateError(self.m.gt("The match is not on the draft stage."))
		elif (team := find(lambda t: author in t[:1], self.m.teams[:2])) is None:
			raise bot.Exc.PermissionError(self.m.gt("You are not a captain."))
		elif picker_team is not None and picker_team is not team:
			raise bot.Exc.PermissionError(self.m.gt("Not your turn to pick."))
		elif player not in self.m.teams[2]:
			raise bot.Exc.NotFoundError(self.m.gt("Specified player not in the unpicked list."))

		self.m.teams[2].remove(player)
		team.append(player)
		await self.refresh()

	async def put(self, player, team_name):
		if (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams)) is None:
			raise bot.Exc.SyntaxError(self.m.gt("Specified team name not found."))
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the draft or waiting report stage."))

		find(lambda t: player in t, self.m.teams).remove(player)
		team.append(player)
		await self.refresh()

	async def sub_me(self, author):
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the draft or waiting report stage."))

		if author in self.sub_queue:
			self.sub_queue.remove(author)
			await self.m.qc.success(self.m.gt("You have stopped looking for a substitute."))
		else:
			self.sub_queue.append(author)
			await self.m.qc.success(self.m.gt("You are now looking for a substitute."))

	async def sub_for(self, author, player):
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the draft or waiting report stage."))
		elif player not in self.sub_queue:
			raise bot.Exc.PermissionError(self.m.gt("Specified player is not looking for a substitute."))

		team = find(lambda t: player in t, self.m.teams)
		team[team.index(player)] = author
		self.m.players.remove(player)
		self.m.players.append(author)
		self.sub_queue.remove(player)
		self.m.ratings = {
			p['user_id']: p['rating'] for p in await self.m.qc.rating.get_players((p.id for p in self.m.players))
		}
		await self.print()
