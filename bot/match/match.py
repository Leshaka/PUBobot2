# -*- coding: utf-8 -*-
from time import time
from itertools import combinations
import random
from discord import Embed, Colour

import bot
from core.client import dc
from core.utils import find, iter_to_dict

from .check_in import CheckIn
from .draft import Draft


class Match:

	INIT = 0
	CHECK_IN = 1
	DRAFT = 2
	WAITING_REPORT = 3

	TEAM_EMOJIS = [
		":fox:", ":wolf:", ":dog:", ":bear:", ":panda_face:", ":tiger:", ":lion:", ":pig:", ":octopus:", ":boar:",
		":scorpion:", ":crab:", ":eagle:", ":shark:", ":bat:", ":rhino:", ":dragon_face:", ":deer:"
	]

	class Team(list):
		def __init__(self, name=None, emoji=None, players=None, idx=-1):
			super().__init__(players or [])
			self.name = name
			self.emoji = emoji
			self.want_draw = False
			self.idx = idx

		def set(self, players):
			self.clear()
			self.extend(players)

		def add(self, p):
			if p not in self:
				self.append(p)

		def rem(self, p):
			if p in self:
				self.remove(p)

	@staticmethod
	def highlight(members):
		if len(members) == 1:
			return f"<@{members[0].id}>"
		else:
			return ", ".join((f"<@{m.id}>" for m in members[:-1])) + f" & <@{members[-1].id}>"

	def __init__(
		self, queue, qc, players, teams=None, team_names=None, team_emojis=None,
		ranked=False, max_players=None, pick_captains="no captains", captains_role_id=None, pick_teams="draft",
		pick_order=None, maps=[], map_count=0, check_in_timeout=0, match_lifetime=0, state_data=None,
		start_msg="Please create an in-game lobby.", start_msg_style="embed"
	):

		# Set parent objects and shorthands
		self.queue = queue
		self.qc = qc
		self.send = qc.channel.send
		self.error = qc.error
		self.gt = qc.gt

		# Set configuration variables
		self.start_msg = start_msg
		self.start_msg_style = start_msg_style
		self.max_players = max_players
		self.pick_teams = pick_teams
		self.ranked = ranked
		self.server = "127.0.0.1"

		# Set working objects
		self.id = 0  # TODO
		self.maps = random.sample(maps, map_count) if len(maps) > map_count else list(maps)
		self.players = list(players)
		# self.ratings = {p['user_id']: p['rating'] for p in await self.qc.rating.get_ratings(self.players)}
		self.ratings = {p.id: 1400 for p in self.players}

		team_names = team_names or ['Alpha', 'Beta']
		team_emojis = team_emojis or random.sample(self.TEAM_EMOJIS, 2)
		self.teams = [
			self.Team(name=team_names[0], emoji=team_emojis[0], idx=0),
			self.Team(name=team_names[1], emoji=team_emojis[1], idx=1),
			self.Team(name="unpicked", emoji="📋", idx=-1)
		]

		self.captains = []
		self.states = []
		self.lifetime = match_lifetime
		self.start_time = int(time())
		self.state = self.INIT

		# Init self sections
		self.init_captains(pick_captains, captains_role_id)
		self.init_teams(pick_teams)
		self.check_in = CheckIn(self, check_in_timeout)
		self.draft = Draft(self, pick_order, captains_role_id)
		if self.ranked:
			print("YAY KEKW")
			self.states.append(self.WAITING_REPORT)

		bot.active_matches.append(self)

	def init_captains(self, pick_captains, captains_role_id):
		if pick_captains == "by role and rating":
			self.captains = sorted(
				self.players,
				key=lambda p: [captains_role_id in [role.id for role in p.roles], self.ratings[p.id]],
				reverse=True
			)
		elif pick_captains == "fair pairs":
			candidates = sorted(self.players, key=lambda p: [self.ratings[p.id]], reverse=True)
			i = random.randrange(len(candidates) - 1)
			self.captains = [candidates[i], candidates[i + 1]]
		elif pick_captains == "random":
			self.captains = random.sample(self.players, 2)

	def init_teams(self, pick_teams):
		if pick_teams == "draft":
			self.teams[0].set(self.captains[:1])
			self.teams[1].set(self.captains[1:])
			self.teams[2].set([p for p in self.players if p not in self.captains])
		elif pick_teams == "matchmaking":
			team_len = int(len(self.players)/2)
			best_rating = sum(self.ratings.values())/2
			best_team = min(
				combinations(self.players, team_len),
				key=lambda team: abs(sum([self.ratings[m.id] for m in team])-best_rating)
			)
			self.teams[0].set(best_team)
			self.teams[1].set((p for p in self.players if p not in best_team))
		elif pick_teams == "random teams":
			self.teams[0].set(random.sample(self.players, int(len(self.players)/2)))
			self.teams[1].set((p for p in self.players if p not in self.teams[0]))

	async def think(self, frame_time):
		if self.state == self.INIT:
			await self.next_state()

		elif self.state == self.CHECK_IN:
			await self.check_in.think(frame_time)

		elif frame_time > self.lifetime + self.start_time:
			pass

	async def next_state(self):
		if len(self.states):
			self.state = self.states.pop(0)
			if self.state == self.CHECK_IN:
				await self.check_in.start()
			elif self.state == self.DRAFT:
				await self.draft.start()
			elif self.state == self.WAITING_REPORT:
				await self.start_waiting_report()
		else:
			if self.state != self.WAITING_REPORT:
				await self.final_message()
			await self.finish_match()

	def rank_str(self, member):
		return self.qc.rating_rank(self.ratings[member.id])['rank']

	async def start_waiting_report(self):
		await self.final_message()

	async def _final_message_embed(self):
		embed = Embed(
			colour=Colour(0x27b75e),
			title=self.qc.gt("__**{queue}** is started!__").format(queue=self.queue.name.capitalize())
		)

		if len(self.teams[0]) == 1 and len(self.teams[1]) == 1:  # 1v1
			p1, p2 = self.teams[0][0], self.teams[1][0]
			players = " \u200b {player1}{rating1}\n \u200b {player2}{rating2}\n\u200b".format(
				rating1=f" \u200b `〈{self.ratings[p1.id]}〉`" if self.ranked else "",
				player1=f"<@{p1.id}>",
				rating2=f" \u200b `〈{self.ratings[p1.id]}〉`" if self.ranked else "",
				player2=f"<@{p2.id}>",
			)
			embed.add_field(name="Players", value=players, inline=False)
		else:  # team vs team
			teams_names = [
				f"{t.emoji} \u200b **{t.name}**" +
				(f" \u200b `〈{sum((self.ratings[p.id] for p in t))}〉`" if self.ranked else "")
				for t in self.teams[:2]
			]
			team_players = [
				" \u200b " +
				" \u200b ".join([
					(f"`{self.rank_str(p)}`" if self.ranked else "") + f"<@{p.id}>"
					for p in t
				])
				for t in self.teams[:2]
			]
			team_players[1] += "\n\u200b"  # Extra empty line
			embed.add_field(name=teams_names[0], value=team_players[0], inline=False)
			embed.add_field(name=teams_names[1], value=team_players[1], inline=False)

		if len(self.maps):
			embed.add_field(
				name=self.qc.gt("Map" if len(self.maps) == 1 else "Maps"),
				value="\n".join((f"**{i}**" for i in self.maps)),
				inline=True
			)
		if self.server:
			embed.add_field(name=self.qc.gt("Server"), value=f"`{self.server}`", inline=True)
		if self.start_msg:
			embed.add_field(name="—", value=self.start_msg, inline=False)
		embed.set_footer(
			text="Match id: 157947",
			icon_url=f"https://cdn.discordapp.com/avatars/{dc.user.id}/{dc.user.avatar}.png?size=64"
		)

		await self.qc.channel.send(embed=embed)

	async def report(self, member=None, team_name=None, draw=False, force=False):
		# TODO: Only captain must be able to do this
		if self.state != self.WAITING_REPORT:
			await self.error(self.gt("The match must be on the waiting report stage."))
			return

		if member:
			team = find(lambda t: member in t, self.teams[:2])
		elif team_name:
			team = find(lambda t: t.name.lower() == team_name, self.teams[:2])
		else:
			team = self.teams[0]

		if team is None:
			await self.error(self.gt("Team not found."))
			return

		e_team = self.teams[abs(team.idx-1)]

		if not force and (draw and not e_team.want_draw):
			team.want_draw = True
			await self.qc.channel.send(
				self.gt("{team} team captain is calling a draw, waiting for {enemy} to type `{prefix}rd`.")
			)
			return

		before = [
			await self.qc.rating.get_ratings((p.id for p in e_team)),
			await self.qc.rating.get_ratings((p.id for p in team))
		]
		results = self.qc.rating.rate(
			winners=before[0],
			losers=before[1],
			draw=draw)

		print(results)
		await self.qc.rating.set_ratings(results)

		before = iter_to_dict((*before[0], *before[1]), key='user_id')
		after = iter_to_dict(results, key='user_id')
		await self.print_rating_results(e_team, team, before, after)

		await self.finish_match()

	async def print_rating_results(self, winners, losers, before, after):
		msg = "```markdown\n"
		msg += f"{self.queue.name.capitalize()}({self.id}) results\n"
		msg += "-------------\n"

		if len(winners) == 1 and len(losers) == 1:
			p = winners[0]
			msg += f"1. {p.nick or p.name} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}\n"
			p = losers[0]
			msg += f"2. {p.nick or p.name} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}"
		else:
			n = 0
			for team in (winners, losers):
				avg_bf = int(sum((before[p.id]['rating'] for p in team))/len(team))
				avg_af = int(sum((after[p.id]['rating'] for p in team))/len(team))
				msg += f"{n}. {team.name} {avg_bf} ⟼ {avg_af}\n"
				msg += "\n".join(
					(f"> {p.name or p.nick} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}" for p in team)
				)
				n += 1
		msg += "```"
		await self.qc.channel.send(msg)

	async def final_message(self):
		#  Embed message with teams
		await self._final_message_embed()

	async def finish_match(self):
		bot.active_matches.remove(self)
