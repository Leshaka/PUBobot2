from nextcord import Message, Embed

from bot import QueueChannel
from core.utils import error_embed, ok_embed

from ..context import Context


class MessageContext(Context):
	""" Context for the text message commands """

	def __init__(self, qc: QueueChannel, message: Message):
		self.message = message
		super().__init__(qc, message.channel, message.author)

	async def reply(self, content: str = None, embed: Embed = None):
		await self.message.reply(content=content, embed=embed)

	async def notice(self, content: str = None, embed: Embed = None):
		await (self.message.thread or self.message.channel).send(content=content, embed=embed)

	async def error(self, *args, **kwargs):
		await self.message.reply(embed=error_embed(*args, **kwargs))

	async def success(self, *args, **kwargs):
		await self.message.reply(embed=ok_embed(*args, **kwargs))