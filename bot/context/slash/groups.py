from nextcord import Interaction

from core.client import dc

GUILD_ID = 745999774649679923


@dc.slash_command(name='channel', guild_ids=[GUILD_ID])
async def admin_channel(interaction: Interaction):
	pass


@dc.slash_command(name='queue', guild_ids=[GUILD_ID])
async def admin_queue(interaction: Interaction):
	pass


@dc.slash_command(name='match', guild_ids=[GUILD_ID])
async def admin_match(interaction: Interaction):
	pass


@dc.slash_command(name='rating', guild_ids=[GUILD_ID])
async def admin_rating(interaction: Interaction):
	pass


@dc.slash_command(name='stats', guild_ids=[GUILD_ID])
async def admin_stats(interaction: Interaction):
	pass


@dc.slash_command(name='noadds', guild_ids=[GUILD_ID])
async def admin_noadds(interaction: Interaction):
	pass


@dc.slash_command(name='phrases', guild_ids=[GUILD_ID])
async def admin_phrases(interaction: Interaction):
	pass
