from nextcord import Interaction

from core.utils import ok_embed, error_embed

from bot import QueueChannel

from ..context import Context


class SlashContext(Context):
	""" Context for the slash message commands """

	def __init__(self, qc: QueueChannel, interaction: Interaction):
		self.interaction = interaction
		super().__init__(qc, interaction.channel, interaction.user)

	async def reply(self, *args, **kwargs):
		if not self.interaction.response.is_done():
			await self.interaction.response.send_message(*args, **kwargs)
		else:
			await self.interaction.followup.send(*args, **kwargs)

	async def reply_dm(self, *args, **kwargs):
		if not self.interaction.response.is_done():
			await self.interaction.response.send_message(*args, **kwargs, ephemeral=True)
		else:
			await self.interaction.user.send(*args, **kwargs)

	async def notice(self, *args, **kwargs):
		if not self.interaction.response.is_done():
			await self.interaction.response.send_message(*args, **kwargs)
		else:
			await self.interaction.channel.send(*args, **kwargs)

	async def ignore(self, *args, **kwargs):
		if not self.interaction.response.is_done():
			await self.interaction.response.send_message(*args, **kwargs, ephemeral=True)

	async def error(self, *args, **kwargs):
		if not self.interaction.response.is_done():
			await self.interaction.response.send_message(embed=error_embed(*args, **kwargs), ephemeral=True)
		else:  # this probably should never happen
			await self.interaction.followup.send(embed=error_embed(*args, **kwargs))

	async def success(self, *args, **kwargs):
		await self.reply(embed=ok_embed(*args, **kwargs))
