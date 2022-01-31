# -*- coding: utf-8 -*-
import random
import bot
from nextcord.errors import DiscordException

from core.utils import join_and
from core.console import log


class CheckIn:

	READY_EMOJI = "☑"
	NOT_READY_EMOJI = "⛔"
	INT_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6⃣", "7⃣", "8⃣", "9⃣"]

	def __init__(self, match, timeout):
		self.m = match
		self.timeout = timeout
		self.allow_discard = self.m.cfg['check_in_discard']
		self.ready_players = set()
		self.message = None

		for p in (p for p in self.m.players if p.id in bot.auto_ready.keys()):
			self.ready_players.add(p)
			bot.auto_ready.pop(p.id)

		if len(self.m.cfg['maps']) > 1 and self.m.cfg['vote_maps']:
			self.maps = self.m.random_maps(self.m.cfg['maps'], self.m.cfg['vote_maps'], self.m.queue.last_maps)
			self.map_votes = [set() for i in self.maps]
		else:
			self.maps = []
			self.map_votes = []

		if self.timeout:
			self.m.states.append(self.m.CHECK_IN)

	async def think(self, frame_time):
		if frame_time > self.m.start_time + self.timeout:
			if self.allow_discard:
				await self.abort_timeout()
			else:
				await self.finish()

	async def start(self):
		text = f"!spawn message {self.m.id}"
		self.message = await self.m.send(text)

		emojis = [self.READY_EMOJI, '🔸', self.NOT_READY_EMOJI] if self.allow_discard else [self.READY_EMOJI]
		emojis += [self.INT_EMOJIS[n] for n in range(len(self.maps))]
		try:
			for emoji in emojis:
				await self.message.add_reaction(emoji)
		except DiscordException:
			pass
		bot.waiting_reactions[self.message.id] = self.process_reaction
		await self.refresh()

	async def refresh(self):
		not_ready = list(filter(lambda m: m not in self.ready_players, self.m.players))
		if len(not_ready):
			try:
				await self.message.edit(content=None, embed=self.m.embeds.check_in(not_ready))
			except DiscordException:
				pass
		else:
			await self.finish()

	async def finish(self):
		bot.waiting_reactions.pop(self.message.id)
		self.ready_players = set()
		if len(self.maps):
			order = list(range(len(self.maps)))
			random.shuffle(order)
			order.sort(key=lambda n: len(self.map_votes[n]), reverse=True)
			self.m.maps = [self.maps[n] for n in order[:self.m.cfg['map_count']]]
		await self.message.delete()
		await self.m.next_state()

	async def process_reaction(self, reaction, user, remove=False):
		if self.m.state != self.m.CHECK_IN or user not in self.m.players:
			return

		if str(reaction) in self.INT_EMOJIS:
			idx = self.INT_EMOJIS.index(str(reaction))
			if idx <= len(self.maps):
				if remove:
					self.map_votes[idx].discard(user.id)
					self.ready_players.discard(user)
				else:
					self.map_votes[idx].add(user.id)
					self.ready_players.add(user)
				await self.refresh()

		elif str(reaction) == self.READY_EMOJI:
			if remove:
				self.ready_players.discard(user)
			else:
				self.ready_players.add(user)
			await self.refresh()

		elif str(reaction) == self.NOT_READY_EMOJI and self.allow_discard:
			await self.abort_member(user)

	async def set_ready(self, member, ready):
		if self.m.state != self.m.CHECK_IN:
			raise bot.Exc.MatchStateError(self.m.gt("The match is not on the check-in stage."))
		if ready:
			self.ready_players.add(member)
			await self.refresh()
		elif not ready:
			if not self.allow_discard:
				raise bot.Exc.PermissionError(self.m.gt("Discarding check-in is not allowed."))
			await self.abort_member(member)

	async def abort_member(self, member):
		bot.waiting_reactions.pop(self.message.id)
		await self.message.delete()
		await self.m.send("\n".join((
			self.m.gt("{member} has aborted the check-in.").format(member=f"<@{member.id}>"),
			self.m.gt("Reverting {queue} to the gathering stage...").format(queue=f"**{self.m.queue.name}**")
		)))

		bot.active_matches.remove(self.m)
		await self.m.queue.revert([member], [m for m in self.m.players if m != member])

	async def abort_timeout(self):
		not_ready = [m for m in self.m.players if m not in self.ready_players]
		if self.message:
			bot.waiting_reactions.pop(self.message.id, None)
			try:
				await self.message.delete()
			except DiscordException:
				pass

		bot.active_matches.remove(self.m)

		await self.m.send("\n".join((
			self.m.gt("{members} was not ready in time.").format(members=join_and([m.mention for m in not_ready])),
			self.m.gt("Reverting {queue} to the gathering stage...").format(queue=f"**{self.m.queue.name}**")
		)))

		await self.m.queue.revert(not_ready, list(self.ready_players))
