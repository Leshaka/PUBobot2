# -*- coding: utf-8 -*-
from time import time
from itertools import combinations
import random
from discord import DiscordException

import bot
from core.utils import find, get, iter_to_dict, join_and, get_nick
from core.client import dc

from .check_in import CheckIn
from .draft import Draft
from .embeds import Embeds


class Match:

	INIT = 0
	CHECK_IN = 1
	DRAFT = 2
	WAITING_REPORT = 3

	TEAM_EMOJIS = [
		":fox:", ":wolf:", ":dog:", ":bear:", ":panda_face:", ":tiger:", ":lion:", ":pig:", ":octopus:", ":boar:",
		":scorpion:", ":crab:", ":eagle:", ":shark:", ":bat:", ":rhino:", ":dragon_face:", ":deer:"
	]

	default_cfg = dict(
		teams=None, team_names=['Alpha', 'Beta'], team_emojis=None, ranked=False,
		team_size=1, pick_captains="no captains", captains_role_id=None, pick_teams="draft",
		pick_order=None, maps=[], vote_maps=0, map_count=0, check_in_timeout=0,
		check_in_discard=True, match_lifetime=3*60*60, start_msg=None, server=None
	)

	class Team(list):
		""" Team is basically a set of member objects, but we need it ordered so list is used """

		def __init__(self, name=None, emoji=None, players=None, idx=-1):
			super().__init__(players or [])
			self.name = name
			self.emoji = emoji
			self.draw_flag = False  # 1 - wants draw; 2 - wants cancel
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

	@classmethod
	async def new(cls, queue, qc, players, **kwargs):
		# Create the Match object
		ratings = {p['user_id']: p['rating'] for p in await qc.rating.get_players((p.id for p in players))}
		bot.last_match_id += 1
		match = cls(bot.last_match_id, queue, qc, players, ratings, **kwargs)
		# Prepare the Match object
		match.maps = match.random_maps(match.cfg['maps'], match.cfg['map_count'], queue.last_maps)
		match.init_captains(match.cfg['pick_captains'], match.cfg['captains_role_id'])
		match.init_teams(match.cfg['pick_teams'])
		if match.ranked:
			match.states.append(match.WAITING_REPORT)
		bot.active_matches.append(match)

	@classmethod
	async def fake_ranked_match(cls, queue, qc, winners, losers, draw=False, **kwargs):
		players = winners + losers
		if len(set(players)) != len(players):
			raise bot.Exc.ValueError("Players list can not contains duplicates.")
		ratings = {p['user_id']: p['rating'] for p in await qc.rating.get_players((p.id for p in players))}
		bot.last_match_id += 1
		match = cls(bot.last_match_id, queue, qc, players, ratings, pick_teams="premade", **kwargs)
		match.teams[0].set(winners)
		match.teams[1].set(losers)
		match.winner = None if draw else 0
		await bot.stats.register_match_ranked(match)

	def serialize(self):
		return dict(
			match_id=self.id,
			queue_id=self.queue.id,
			channel_id=self.qc.id,
			cfg=self.cfg,
			players=[p.id for p in self.players if p],
			teams=[[p.id for p in team if p] for team in self.teams],
			maps=self.maps,
			state=self.state,
			states=self.states,
			ready_players=[p.id for p in self.check_in.ready_players if p]
		)

	@classmethod
	async def from_json(cls, queue, qc, data):
		# Prepare discord objects
		data['players'] = [qc.channel.guild.get_member(user_id) for user_id in data['players']]
		if None in data['players']:
			await qc.error(f"Unable to load match {data['match_id']}, error fetching guild members.")
			return

		# Fill data with discord objects
		for i in range(len(data['teams'])):
			data['teams'][i] = [get(data['players'], id=user_id) for user_id in data['teams'][i]]
		data['ready_players'] = [get(data['players'], id=user_id) for user_id in data['ready_players']]

		# Create the Match object
		ratings = {p['user_id']: p['rating'] for p in await qc.rating.get_players((p.id for p in data['players']))}
		bot.last_match_id += 1
		match = cls(bot.last_match_id, queue, qc, data['players'], ratings, **data['cfg'])

		# Set state data
		for i in range(len(match.teams)):
			match.teams[i].set(data['teams'][i])
		match.check_in.ready_players = set(data['ready_players'])
		match.maps = data['maps']
		match.state = data['state']
		match.states = data['states']
		if match.state == match.CHECK_IN:
			await match.check_in.start()  # Spawn a new check_in message

		bot.active_matches.append(match)

	def __init__(self, match_id, queue, qc, players, ratings, **cfg):

		# Set parent objects and shorthands
		self.queue = queue
		self.qc = qc
		self.send = qc.channel.send
		self.gt = qc.gt

		# Set configuration variables
		cfg = {k: v for k, v in cfg.items() if v is not None}  # filter kwargs for notnull values
		self.cfg = self.default_cfg.copy()
		self.cfg.update(cfg)

		# Set working objects
		self.id = match_id
		self.ranked = self.cfg['ranked'] and self.cfg['pick_teams'] != 'no teams'
		self.players = list(players)
		self.ratings = ratings
		self.winner = None

		team_names = self.cfg['team_names']
		team_emojis = self.cfg['team_emojis'] or random.sample(self.TEAM_EMOJIS, 2)
		self.teams = [
			self.Team(name=team_names[0], emoji=team_emojis[0], idx=0),
			self.Team(name=team_names[1], emoji=team_emojis[1], idx=1),
			self.Team(name="unpicked", emoji="📋", idx=-1)
		]

		self.captains = []
		self.states = []
		self.maps = []
		self.lifetime = self.cfg['match_lifetime']
		self.start_time = int(time())
		self.state = self.INIT

		# Init self sections
		self.check_in = CheckIn(self, self.cfg['check_in_timeout'])
		self.draft = Draft(self, self.cfg['pick_order'], self.cfg['captains_role_id'])
		self.embeds = Embeds(self)

	@staticmethod
	def random_maps(maps, map_count, last_maps=None):
		for last_map in (last_maps or [])[::-1]:
			if last_map in maps and map_count < len(maps):
				maps.remove(last_map)

		return random.sample(maps, min(map_count, len(maps)))

	def sort_players(self, players):
		""" sort given list of members by captains role and rating """
		return sorted(
			players,
			key=lambda p: [self.cfg['captains_role_id'] in [role.id for role in p.roles], self.ratings[p.id]],
			reverse=True
		)

	def init_captains(self, pick_captains, captains_role_id):
		if pick_captains == "by role and rating":
			self.captains = self.sort_players(self.players)[:2]
		elif pick_captains == "fair pairs":
			candidates = sorted(self.players, key=lambda p: [self.ratings[p.id]], reverse=True)
			i = random.randrange(len(candidates) - 1)
			self.captains = [candidates[i], candidates[i + 1]]
		elif pick_captains == "random":
			self.captains = random.sample(self.players, 2)
		elif pick_captains == "random with role preference":
			rand = random.sample(self.players, len(self.players))
			self.captains = sorted(
				rand, key=lambda p: self.cfg['captains_role_id'] in [role.id for role in p.roles], reverse=True
			)[:2]

	def init_teams(self, pick_teams):
		if pick_teams == "draft":
			self.teams[0].set(self.captains[:1])
			self.teams[1].set(self.captains[1:])
			self.teams[2].set([p for p in self.players if p not in self.captains])
		elif pick_teams == "matchmaking":
			team_len = min(self.cfg['team_size'], int(len(self.players)/2))
			best_rating = sum(self.ratings.values())/2
			best_team = min(
				combinations(self.players, team_len),
				key=lambda team: abs(sum([self.ratings[m.id] for m in team])-best_rating)
			)
			self.teams[0].set(self.sort_players(
				best_team[:self.cfg['team_size']]
			))
			self.teams[1].set(self.sort_players(
				[p for p in self.players if p not in best_team][:self.cfg['team_size']]
			))
			self.teams[2].set([p for p in self.players if p not in [*self.teams[0], *self.teams[1]]])
		elif pick_teams == "random teams":
			self.teams[0].set(random.sample(self.players, min(len(self.players)//2, self.cfg['team_size'])))
			self.teams[1].set([p for p in self.players if p not in self.teams[0]][:self.cfg['team_size']])
			self.teams[2].set([p for p in self.players if p not in [*self.teams[0], *self.teams[1]]])

	async def think(self, frame_time):
		if self.state == self.INIT:
			await self.next_state()

		elif self.state == self.CHECK_IN:
			await self.check_in.think(frame_time)

		elif frame_time > self.lifetime + self.start_time:
			try:
				await self.qc.error(self.gt("Match {queue} ({id}) has timed out.").format(
					queue=self.queue.name,
					id=self.id
				))
			except DiscordException:
				pass
			await self.cancel()

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
		# remove never picked players from the match
		if len(self.teams[2]):
			for p in self.teams[2]:
				self.players.remove(p)
			await self.send(self.gt("{players} were removed from the match.").format(
				players=join_and([m.mention for m in self.teams[2]])
			))
			self.teams[2].clear()
		await self.final_message()

	async def report_loss(self, member, draw_flag):
		if self.state != self.WAITING_REPORT:
			raise bot.Exc.MatchStateError(self.gt("The match must be on the waiting report stage."))

		team = find(lambda team: member in team[:1], self.teams[:2])
		if team is None:
			raise bot.Exc.PermissionError(self.gt("You must be a team captain to report a loss or draw."))

		enemy_team = self.teams[1-team.idx]
		if draw_flag and not enemy_team.draw_flag == draw_flag:
			team.draw_flag = draw_flag
			await self.qc.channel.send(
				self.gt(
					"{self} is calling a draw, waiting for {enemy} to type `{prefix}rd`." if draw_flag == 1 else
					"{self} offers to cancel the match, waiting for {enemy} to type `{prefix}rc`."
				).format(
					self=member.mention,
					enemy=enemy_team[0].mention,
					prefix=self.qc.cfg.prefix
				)
			)
			return

		if draw_flag == 2:
			await self.cancel()
			return

		elif draw_flag == 1:
			self.winner = None
		else:
			self.winner = enemy_team.idx
		await self.finish_match()

	async def report_win(self, team_name):  # version for admins/mods
		if self.state != self.WAITING_REPORT:
			raise bot.Exc.MatchStateError(self.gt("The match must be on the waiting report stage."))

		team_name = team_name.lower()
		if team_name == "draw":
			self.winner = None
		elif (team := find(lambda t: t.name.lower() == team_name, self.teams[:2])) is not None:
			self.winner = team.idx
		else:
			raise bot.Exc.SyntaxError(self.gt("Specified team name not found."))

		await self.finish_match()

	async def print_rating_results(self, before, after):
		msg = "```markdown\n"
		msg += f"{self.queue.name.capitalize()}({self.id}) results\n"
		msg += "-------------"

		if self.winner is not None:
			winners, losers = self.teams[self.winner], self.teams[abs(self.winner-1)]
		else:
			winners, losers = self.teams[:2]

		if len(winners) == 1 and len(losers) == 1:
			p = winners[0]
			msg += f"\n1. {get_nick(p)} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}"
			p = losers[0]
			msg += f"\n2. {get_nick(p)} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}"
		else:
			n = 0
			for team in (winners, losers):
				avg_bf = int(sum((before[p.id]['rating'] for p in team))/len(team))
				avg_af = int(sum((after[p.id]['rating'] for p in team))/len(team))
				msg += f"\n{n}. {team.name} {avg_bf} ⟼ {avg_af}\n"
				msg += "\n".join(
					(f"> {get_nick(p)} {before[p.id]['rating']} ⟼ {after[p.id]['rating']}" for p in team)
				)
				n += 1
		msg += "```"
		await self.qc.channel.send(msg)

	async def final_message(self):
		#  Embed message with teams
		try:
			await self.qc.channel.send(embed=self.embeds.final_message())
		except DiscordException:
			pass

	async def finish_match(self):
		bot.active_matches.remove(self)
		self.queue.last_maps += self.maps
		self.queue.last_maps = self.queue.last_maps[-len(self.maps)*self.queue.cfg.map_cooldown:]

		if self.ranked:
			await bot.stats.register_match_ranked(self)
		else:
			await bot.stats.register_match_unranked(self)

	def print(self):
		return f"> *({self.id})* **{self.queue.name}** | `{join_and([get_nick(p) for p in self.players])}`"

	async def cancel(self):
		if self.check_in.message and self.check_in.message.id in bot.waiting_reactions.keys():
			bot.waiting_reactions.pop(self.check_in.message.id)
		try:
			await self.qc.channel.send(
				self.gt("{players} your match has been canceled.").format(players=join_and([p.mention for p in self.players]))
			)
		except DiscordException:
			pass
		bot.active_matches.remove(self)
