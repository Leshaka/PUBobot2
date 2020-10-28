# -*- coding: utf-8 -*-
import bot


class CheckIn:

	READY_EMOJI = "☑"
	NOT_READY_EMOJI = "⛔"

	def __init__(self, match, timeout):
		self.m = match
		self.timeout = timeout
		self.ready_players = []
		self.message = None

		if self.timeout:
			self.m.states.append(self.m.CHECK_IN)

	async def think(self, frame_time):
		if frame_time > self.m.start_time + self.timeout:
			await self.abort_timeout()

	async def start(self):
		text = f"!spawn message {self.m.id}"
		bot.waiting_messages.append([self.m.qc.channel.id, text, self.spawn_message])
		await self.m.send(text)

	async def spawn_message(self, message):
		self.message = message
		for emoji in [self.READY_EMOJI, '🔸', self.NOT_READY_EMOJI]:
			await message.add_reaction(emoji)
		bot.waiting_reactions[self.message.id] = self.process_reaction
		await self.refresh()

	async def refresh(self):
		not_ready = list(filter(lambda m: m not in self.ready_players, self.m.players))
		if len(not_ready):
			await self.message.edit(content=self.m.gt("\n".join([
				self.m.gt("__**{queue}** is now on the check-in stage!__"),
				self.m.gt("Waiting on: {players}."),
				self.m.gt("Please react with {ready_emoji} to **check-in** or {not_ready_emoji} to **abort**!")
			])).format(
				queue=self.m.queue.name, players=self.m.highlight(not_ready),
				ready_emoji=self.READY_EMOJI, not_ready_emoji=self.NOT_READY_EMOJI
			))
		else:
			bot.waiting_reactions.pop(self.message.id)
			self.ready_players = []
			await self.message.delete()
			await self.m.next_state()

	async def process_reaction(self, reaction, user, remove=False):
		if self.m.state != self.m.CHECK_IN or user not in self.m.players:
			return

		print(self.ready_players, remove)
		print(user in self.ready_players)
		if str(reaction) == self.READY_EMOJI:
			if remove and user in self.ready_players:
				print("Quack!!!")
				self.ready_players.remove(user)
			elif not remove and user not in self.ready_players:
				self.ready_players.append(user)
			await self.refresh()

		if str(reaction) == self.NOT_READY_EMOJI and user in self.m.players:
			await self.abort_member(user)

	async def set_ready(self, member, ready):
		if self.m.state != self.m.CHECK_IN:
			await self.m.error(self.m.gt("The match is not on the check-in stage."))
		if ready and member not in self.ready_players:
			self.ready_players.append(member)
			await self.refresh()
		elif not ready:
			await self.abort_member(member)

	async def abort_member(self, member):
		bot.waiting_reactions.pop(self.message.id)
		await self.message.delete()
		await self.m.send("\n".join((
			self.m.gt("{member} has aborted the check-in.").format(member=f"<@{member.id}>"),
			self.m.gt("Reverting {queue} to the gathering stage...").format(queue=f"**{self.m.queue.name}**")
		)))

		bot.active_matches.remove(self)
		await self.m.queue.revert([member], [m for m in self.m.players if m != member])

	async def abort_timeout(self):
		not_ready = [m for m in self.m.players if m not in self.ready_players]
		bot.waiting_reactions.pop(self.message.id)
		await self.message.delete()
		await self.m.send("\n".join((
			self.m.gt("{members} was not ready in time.").format(members=self.m.highlight(not_ready)),
			self.m.gt("Reverting {queue} to the gathering stage...").format(queue=f"**{self.m.queue.name}**")
		)))

		await self.m.queue.revert(not_ready, self.ready_players)
		print(bot.active_matches)
		bot.active_matches.remove(self)
