from nextcord import abc
from nextcord import Member, Embed
from enum import IntEnum
import re

import bot

from core.config import cfg
from core.utils import error_embed, ok_embed, find
from core.client import FakeMember, dc
from core.console import log


class Context:
	"""
	Context data base class for each type of interaction
	such as text message, web interaction, slash command, button press etc
	belonging to a QueueChannel object.
	"""

	class Perms(IntEnum):
		USER = 0
		MEMBER = 1
		MODERATOR = 2
		ADMIN = 3

	def __init__(self, qc: bot.QueueChannel, channel: abc.GuildChannel, author: Member):
		self.qc = qc
		self.channel = channel
		self.author = author

	async def get_member(self, mention):
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
		""" Get the author permissions """
		if (self.qc.cfg.admin_role in self.author.roles or
					self.author.id == cfg.DC_OWNER_ID or
					self.channel.permissions_for(self.author).administrator):
			return self.Perms.ADMIN
		elif self.qc.cfg.moderator_role in self.author.roles:
			return self.Perms.MODERATOR
		else:
			return self.Perms.MEMBER

	def check_perms(self, req_perms: Perms):
		""" Raise PermissionError if specified permissions is not met by the author """
		if self.access_level.value < req_perms.value:
			if req_perms == 2:
				raise bot.Exc.PermissionError(self.qc.gt("You must possess admin permissions."))
			else:
				raise bot.Exc.PermissionError(self.qc.gt("You must possess moderator permissions."))

	async def reply(self, content: str = None, embed: Embed = None):
		""" Reply in public chat """
		pass

	async def reply_dm(self, content: str = None, embed: Embed = None):
		""" Reply in DM or only visibly by the author """
		pass

	async def notice(self, content: str = None, embed: Embed = None):
		""" Send message in chat without replying if possible """
		pass

	async def ignore(self, content: str = None, embed: Embed = None):
		""" Send reply only if it's required to reply by the context class """
		pass

	async def error(self, content: str, title: str = None):
		""" Reply an error embed """
		pass

	async def success(self, content: str, title: str = None):
		""" Reply an ok embed """
		pass


class SystemContext(Context):
	""" Context for background processes and console commands """

	def __init__(self, qc: bot.QueueChannel, thread_id=None):
		if (channel := dc.get_channel(qc.id)) is None:
			raise IndexError("Missing discord channel for {}>#{} ({}).".format(
				qc.cfg.cfg_info.get('guild_name'), qc.cfg.cfg_info.get('channel_name'), qc.id
			))
		if thread_id:
			self.thread = channel.get_thread(thread_id)
		else:
			self.thread = None
		self.messagable = self.thread or channel
		super().__init__(qc, channel, dc.user)

	def check_perms(self, req_perms: Context.Perms):
		pass

	def access_level(self):
		return Context.Perms.ADMIN

	async def reply(self, content: str = None, embed: Embed = None):
		await self.messagable.send(content=content, embed=embed)

	async def notice(self, content: str = None, embed: Embed = None):
		""" Send message in chat without replying if possible """
		await self.messagable.send(content=content, embed=embed)

	async def reply_dm(self, content: str = None, embed: Embed = None):
		await self.messagable.send(content=content, embed=embed)

	async def error(self, *args, **kwargs):
		await self.messagable.send(embed=error_embed(*args, **kwargs))

	async def success(self, *args, **kwargs):
		await self.messagable.send(embed=ok_embed(*args, **kwargs))


class WebContext(Context):
	""" Context for actions within the web interface """

	def __init__(self, user_id: int, channel_id: int):
		if (qc := bot.queue_channels.get(channel_id)) is None:
			raise bot.Exc.NotFoundError(f"QueueChannel with id {channel_id} is not found.")
		if (channel := dc.get_channel(channel_id)) is None:
			raise bot.Exc.NotFoundError(f"Discord Channel object with id {channel_id} is not reachable.")
		if (author := channel.guild.get_member(user_id)) is None:
			raise bot.Exc.NotFoundError(f"You are not a member of requested guild.")

		super().__init__(qc, channel, author)
