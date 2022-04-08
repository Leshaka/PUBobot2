# -*- coding: utf-8 -*-
import bot
from core.utils import find
from nextcord import DiscordException


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

	async def start(self, ctx):
		await self.refresh(ctx)

	async def print(self, ctx):
		try:
			await ctx.notice(embed=self.m.embeds.draft())
		except DiscordException:
			pass

	async def refresh(self, ctx):
		if self.m.state != self.m.DRAFT:
			await self.print(ctx)
		elif len(self.m.teams[2]) and any((len(t) < self.m.cfg['team_size'] for t in self.m.teams)):
			await self.print(ctx)
		else:
			await self.m.next_state(ctx)

	async def cap_for(self, ctx, author, team_name):
		if self.m.state != self.m.DRAFT:
			raise bot.Exc.MatchStateError(self.m.gt("The match is not on the draft stage."))
		elif self.captains_role_id and self.captains_role_id not in (r.id for r in author.roles):
			raise bot.Exc.PermissionError(self.m.gt("You must possess the captain's role."))
		elif (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams[:2])) is None:
			raise bot.Exc.SyntaxError(self.m.gt("Specified team name not found."))

		if len(team):
			# raise bot.Exc.PermissionError(self.m.gt("Team {name} already have a captain.".format(name=f"**{team.name}**")))
			self.m.teams[2].append(team.pop(0))

		find(lambda t: author in t, self.m.teams).remove(author)
		team.insert(0, author)
		await self.print(ctx)

	async def pick(self, ctx, author, players):
		for player in players:
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

			# auto last-pick rest of the players if possible
			# if rest of pick_order covers the unpicked list
			if len(self.m.teams[2]) and len(self.pick_order[pick_step+1:]) >= len(self.m.teams[2]):
				# if rest of pick_order is a single team
				if len(set(self.pick_order[pick_step+1:])) == 1:
					picker_team = self.m.teams[self.pick_order[pick_step+1]]
					picker_team.extend(self.m.teams[2])
					self.m.teams[2].clear()

		await self.refresh(ctx)

	async def put(self, ctx, player, team_name):
		if (team := find(lambda t: t.name.lower() == team_name.lower(), self.m.teams)) is None:
			raise bot.Exc.SyntaxError(self.m.gt("Specified team name not found."))
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the draft or waiting report stage."))

		if (old_team := find(lambda t: player in t, self.m.teams)) is not None:
			old_team.remove(player)
		else:
			self.m.players.append(player)
			self.m.ratings = {
				p['user_id']: p['rating'] for p in await self.m.qc.rating.get_players((p.id for p in self.m.players))
			}

		team.append(player)
		await self.m.qc.remove_members(player, ctx=ctx)
		await self.refresh(ctx)

	async def sub_me(self, ctx, author):
		if self.m.state not in [self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the draft or waiting report stage."))

		if author in self.sub_queue:
			self.sub_queue.remove(author)
			await ctx.success(self.m.gt("You have stopped looking for a substitute."))
		else:
			self.sub_queue.append(author)
			await ctx.success(self.m.gt("You are now looking for a substitute."))

	async def sub_for(self, ctx, player1, player2, force=False):
		if self.m.state not in [self.m.CHECK_IN, self.m.DRAFT, self.m.WAITING_REPORT]:
			raise bot.Exc.MatchStateError(self.m.gt("The match must be on the check-in, draft or waiting report stage."))
		elif not force and player1 not in self.sub_queue:
			raise bot.Exc.PermissionError(self.m.gt("Specified player is not looking for a substitute."))

		team = find(lambda t: player1 in t, self.m.teams)
		team[team.index(player1)] = player2
		self.m.players.remove(player1)
		self.m.players.append(player2)
		if player1 in self.sub_queue:
			self.sub_queue.remove(player1)
		self.m.ratings = {
			p['user_id']: p['rating'] for p in await self.m.qc.rating.get_players((p.id for p in self.m.players))
		}
		await self.m.qc.remove_members(player2, ctx=ctx)
		await bot.remove_players(player2, reason="pickup started")

		if self.m.state == self.m.CHECK_IN:
			await self.m.check_in.refresh()
		elif self.m.state == self.m.WAITING_REPORT:
			await ctx.notice(embed=self.m.embeds.final_message())
		else:
			await self.print(ctx)
