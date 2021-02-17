
class Exceptions:

	class PubobotException(BaseException):
		pass

	class PermissionError(PubobotException):
		pass

	class SyntaxError(PubobotException):
		pass

	class ValueError(PubobotException):
		pass

	class InMatchError(PubobotException):
		pass

	class NotInMatchError(PubobotException):
		pass

	class MatchStateError(PubobotException):
		pass

	class NotFoundError(PubobotException):
		pass
