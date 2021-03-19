# -*- coding: utf-8 -*-
import time
from random import choice
from core.database import db
from core.utils import get_nick

db.ensure_table(dict(
	tname="noadds",
	columns=[
		dict(cname="id", ctype=db.types.int, autoincrement=True),
		dict(cname="guild_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="name", ctype=db.types.str),
		dict(cname="is_active", ctype=db.types.bool, default=1),
		dict(cname="at", ctype=db.types.int),
		dict(cname="duration", ctype=db.types.int),
		dict(cname="reason", ctype=db.types.text),
		dict(cname="by", ctype=db.types.str),
		dict(cname="released_by", ctype=db.types.str)
	],
	primary_keys=["id"]
))

db.ensure_table(dict(
	tname="qc_phrases",
	columns=[
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="phrase", ctype=db.types.text),
	]
))


class NoAdds:

	def __init__(self):
		self.next_tick = 0

	@staticmethod
	async def get_user(qc, member):
		""" returns [ban_left, phrase]"""

		m_noadd = await db.select_one(
			['duration', 'at'], 'noadds', where=dict(guild_id=qc.channel.guild.id, user_id=member.id, is_active=1)
		)
		ban_left = max(0, (m_noadd['duration']+m_noadd['at'])-int(time.time())) if m_noadd else 0
		phrases = await db.select(['phrase'], 'qc_phrases', where=dict(channel_id=qc.channel.id, user_id=member.id))

		return [ban_left, choice(phrases)['phrase'] if len(phrases) else None]

	@staticmethod
	async def phrases_add(qc, member, phrase):
		await db.insert('qc_phrases', dict(channel_id=qc.channel.id, user_id=member.id, phrase=phrase))

	@staticmethod
	async def phrases_clear(qc, member=None):
		if member:
			await db.delete('qc_phrases', where=dict(channel_id=qc.channel.id, user_id=member.id))
		else:
			await db.delete('qc_phrases', where=dict(channel_id=qc.channel.id))

	@staticmethod
	async def noadd(qc, member, duration, moderator, reason=None):
		await db.update(
			'noadds',
			dict(is_active=0, released_by="another noadd"),
			keys=dict(guild_id=qc.channel.guild.id, user_id=member.id, is_active=1)
		)
		await db.insert('noadds', dict(
			guild_id=qc.channel.guild.id,
			user_id=member.id,
			name=get_nick(member),
			at=int(time.time()),
			duration=duration,
			reason=reason,
			by=get_nick(moderator)
		))

	@staticmethod
	async def forgive(qc, member, moderator):
		noadd_id = await db.select_one(
			['id'], 'noadds', where=dict(guild_id=qc.channel.guild.id, user_id=member.id, is_active=1)
		)
		if not noadd_id:
			return False
		await db.update(
			'noadds',
			dict(is_active=0, released_by=get_nick(moderator)),
			keys=noadd_id
		)
		return True

	@staticmethod
	async def get_noadds(qc):
		return await db.select(['*'], 'noadds', where=dict(guild_id=qc.channel.guild.id, is_active=1))

	async def think(self, frame_time):
		if frame_time > self.next_tick:
			await db.execute("UPDATE `noadds` SET is_active=0, released_by='time' WHERE (`at`+`duration`)<%s", (frame_time, ))
			self.next_tick = frame_time + 60


noadds = NoAdds()
