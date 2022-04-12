from nextcord import Interaction

from core.client import dc
from core.config import cfg

guild_kwargs = dict(guild_ids=cfg.DC_SLASH_SERVERS) if len(cfg.DC_SLASH_SERVERS) else dict()


@dc.slash_command(name='channel', **guild_kwargs)
async def admin_channel(interaction: Interaction):
	pass


@dc.slash_command(name='queue', **guild_kwargs)
async def admin_queue(interaction: Interaction):
	pass


@dc.slash_command(name='match', **guild_kwargs)
async def admin_match(interaction: Interaction):
	pass


@dc.slash_command(name='rating', **guild_kwargs)
async def admin_rating(interaction: Interaction):
	pass


@dc.slash_command(name='stats', **guild_kwargs)
async def admin_stats(interaction: Interaction):
	pass


@dc.slash_command(name='noadds', **guild_kwargs)
async def admin_noadds(interaction: Interaction):
	pass


@dc.slash_command(name='phrases', **guild_kwargs)
async def admin_phrases(interaction: Interaction):
	pass
