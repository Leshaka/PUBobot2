from nextcord import abc
from nextcord import Member, Embed, Message
from enum import Enum
import re

import bot

from core.config import cfg
from core.utils import error_embed, ok_embed, find
from core.client import FakeMember


class Context:
	"""
	Context data base class for each type of interaction
	such as text message, web interaction, slash command, button press etc
	belonging to a QueueChannel object.
	"""

	class Perms(Enum):
		USER = 0
		MEMBER = 1
		MODERATOR = 2
		ADMIN = 3

	def __init__(self, qc: bot.QueueChannel, channel: abc.GuildChannel, author: Member):
		self.qc = qc
		self.channel = channel
		self.author = author

	def get_member(self, mention):
		if type(mention) is Member:
			return mention
		elif highlight := re.match(r"<@!?(\d+)>", mention):
			return self.channel.guild.get_member(int(highlight.group(1)))
		elif mask := re.match(r"^(\w+)@(\d{5,20})$", mention):
			name, user_id = mask.groups()
			return FakeMember(guild=self.channel.guild, user_id=int(user_id), name=name)
		else:
			string = mention.lower()
			return find(
				lambda m: string == m.name.lower() or (m.nick and string == m.nick.lower()),
				self.channel.guild.members
			)

	@property
	def access_level(self):
		if (self.qc.cfg.admin_role in self.author.roles or
					self.author.id == cfg.DC_OWNER_ID or
					self.channel.permissions_for(self.author).administrator):
			return self.Perms.ADMIN
		elif self.qc.cfg.moderator_role in self.author.roles:
			return self.Perms.MODERATOR
		else:
			return self.Perms.MEMBER

	def check_perms(self, req_perms: Perms):
		if self.access_level.value < req_perms.value:
			if req_perms == 2:
				raise bot.Exc.PermissionError(self.qc.gt("You must possess admin permissions."))
			else:
				raise bot.Exc.PermissionError(self.qc.gt("You must possess moderator permissions."))

	async def reply(self, content: str = None, embed: Embed = None):
		pass

	async def reply_dm(self, content: str = None, embed: Embed = None):
		pass

	async def notice(self, content: str = None, embed: Embed = None):
		pass

	async def no_effect(self, content: str = None, embed: Embed = None):
		pass

	async def error(self, content: str, title: str = None):
		pass

	async def success(self, content: str, title: str = None):
		pass


class MessageContext(Context):
	""" Context for the text message commands """

	def __init__(self, qc: bot.QueueChannel, message: Message):
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
