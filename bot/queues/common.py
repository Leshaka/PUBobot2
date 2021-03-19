class QueueResponse:
	pass


class QueueResponses:
	class QueueFull(QueueResponse):
		pass

	class QueueStarted(QueueResponse):
		pass

	class Success(QueueResponse):
		pass

	class Duplicate(QueueResponse):
		pass

	class NotAllowed(QueueResponse):
		pass
