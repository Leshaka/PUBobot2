import time
import bot

from core.console import log


class ExpireTimer:

	def __init__(self):
		self.tasks = dict()  # hash: Task()
		self.next = None     # Task()

	def serialize(self):
		return [t.serialize() for t in self.tasks.values()]

	async def load_json(self, data):
		for task_data in data:
			if task := await self.ExpireTask.from_json(task_data):
				self.tasks[task.hash] = task
		self._define_next()

	class ExpireTask:

		def __init__(self, qc, member, at):
			self.qc = qc
			self.member = member
			self.at = at
			self.hash = str(self.qc.channel.id) + "_" + str(self.member.id)

		def serialize(self):
			return {'channel_id': self.qc.channel.id, 'member': self.member.id, 'at': self.at}

		@classmethod
		async def from_json(cls, data):
			if qc := bot.queue_channels.get(data['channel_id']):
				if member := qc.channel.guild.get_member(data['member']):
					return cls(qc, member, data['at'])
			return None

	def set(self, qc, member, delay):
		new_task = self.ExpireTask(qc, member, int(time.time()+delay))
		self.tasks[new_task.hash] = new_task
		log.debug(f"EXPIRE TIMER SET > {member.name} ({qc.id}/{member.id}) to {delay}")
		self._define_next()

	def get(self, qc, member):
		return self.tasks.get(str(qc.channel.id) + "_" + str(member.id))

	def _define_next(self):
		if len(self.tasks):
			self.next = sorted(self.tasks.values(), key=lambda task: task.at)[0]
			log.debug(f"EXPIRE TIMER NEXT > {self.next.member.name} ({self.next.qc.id}/{self.next.member.id})")
		else:
			self.next = None

	def cancel(self, qc, member):
		key = str(qc.channel.id) + "_" + str(member.id)
		if key in self.tasks.keys():
			task = self.tasks.pop(key)
			log.debug(f"EXPIRE TIMER CANCEL > {task.member.name} ({task.qc.id}/{task.member.id})")
			if self.next and self.next.hash == key:
				self._define_next()

	async def think(self, frame_time):
		if self.next and frame_time >= self.next.at:
			task = self.tasks.pop(self.next.hash)
			log.debug(f"EXPIRE TIMER TRIGGER > {task.member.name} ({task.qc.id}/{task.member.id})")
			self._define_next()
			if task.qc and task.member:
				ctx = bot.SystemContext(task.qc)
				await task.qc.remove_members(ctx, task.member, reason="expire", highlight=True)


expire = ExpireTimer()
