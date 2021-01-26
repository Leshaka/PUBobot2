import time


class ExpireTimer:

	def __init__(self):
		self.tasks = dict()  # hash: Task()
		self.next = None     # Task()

	class ExpireTask:

		def __init__(self, qc, member, at):
			self.qc = qc
			self.member = member
			self.at = at
			self.hash = str(self.qc.channel.id) + str(self.member.id)

	def set(self, qc, member, delay):
		new_task = self.ExpireTask(qc, member, int(time.time()+delay))
		self.tasks[new_task.hash] = new_task
		self._define_next()

	def get(self, qc, member):
		return self.tasks.get(str(qc.channel.id) + str(member.id))

	def _define_next(self):
		if len(self.tasks):
			self.next = sorted(self.tasks.values(), key=lambda task: task.at)[0]
		else:
			self.next = None

	def cancel(self, qc, member):
		key = str(qc.channel.id) + str(member.id)
		if key in self.tasks.keys():
			self.tasks.pop(key)
			if self.next and self.next.hash == key:
				self._define_next()

	async def think(self, frame_time):
		if self.next and frame_time >= self.next.at:
			await self.next.qc.remove_members(self.next.member, reason="expire")
			self.tasks.pop(self.next.hash)
			self._define_next()


expire = ExpireTimer()
