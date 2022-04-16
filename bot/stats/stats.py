# -*- coding: utf-8 -*-
import time
import datetime
import asyncio
import bot
from core.console import log
from core.database import db
from core.utils import iter_to_dict, find, get_nick

db.ensure_table(dict(
	tname="players",
	columns=[
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="name", ctype=db.types.str),
		dict(cname="allow_dm", ctype=db.types.bool),
		dict(cname="expire", ctype=db.types.int)
	],
	primary_keys=["user_id"]
))

db.ensure_table(dict(
	tname="qc_players",
	columns=[
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="nick", ctype=db.types.str),
		dict(cname="is_hidden", ctype=db.types.bool, default=0),
		dict(cname="rating", ctype=db.types.int),
		dict(cname="deviation", ctype=db.types.int),
		dict(cname="wins", ctype=db.types.int, notnull=True, default=0),
		dict(cname="losses", ctype=db.types.int, notnull=True, default=0),
		dict(cname="draws", ctype=db.types.int, notnull=True, default=0),
		dict(cname="streak", ctype=db.types.int, notnull=True, default=0)
	],
	primary_keys=["user_id", "channel_id"]
))

db.ensure_table(dict(
	tname="qc_rating_history",
	columns=[
		dict(cname="id", ctype=db.types.int, autoincrement=True),
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="at", ctype=db.types.int),
		dict(cname="rating_before", ctype=db.types.int),
		dict(cname="rating_change", ctype=db.types.int),
		dict(cname="deviation_before", ctype=db.types.int),
		dict(cname="deviation_change", ctype=db.types.int),
		dict(cname="match_id", ctype=db.types.int),
		dict(cname="reason", ctype=db.types.str)
	],
	primary_keys=["id"]
))

db.ensure_table(dict(
	tname="qc_matches",
	columns=[
		dict(cname="match_id", ctype=db.types.int),
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="queue_id", ctype=db.types.int),
		dict(cname="queue_name", ctype=db.types.str),
		dict(cname="at", ctype=db.types.int),
		dict(cname="alpha_name", ctype=db.types.str),
		dict(cname="beta_name", ctype=db.types.str),
		dict(cname="ranked", ctype=db.types.bool),
		dict(cname="winner", ctype=db.types.bool),
		dict(cname="alpha_score", ctype=db.types.int),
		dict(cname="beta_score", ctype=db.types.int),
		dict(cname="maps", ctype=db.types.str)
	],
	primary_keys=["match_id"]
))

db.ensure_table(dict(
	tname="qc_match_id_counter",
	columns=[
		dict(cname="next_id", ctype=db.types.int)
	]
))

db.ensure_table(dict(
	tname="qc_player_matches",
	columns=[
		dict(cname="match_id", ctype=db.types.int),
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="nick", ctype=db.types.str),
		dict(cname="team", ctype=db.types.bool)
	],
	primary_keys=["match_id", "user_id"]
))

db.ensure_table(dict(
	tname="disabled_guilds",
	columns=[
		dict(cname="guild_id", ctype=db.types.int)
	],
	primary_keys=["guild_id"]
))


async def check_match_id_counter():
	"""
	Set to current max match_id+1 if not persist or less
	"""
	m = await db.select_one(('match_id',), 'qc_matches', order_by='match_id', limit=1)
	next_known_match = m['match_id']+1 if m else 0
	counter = await db.select_one(('next_id',), 'qc_match_id_counter')
	if counter is None:
		await db.insert('qc_match_id_counter', dict(next_id=next_known_match))
	elif next_known_match > counter['next_id']:
		await db.update('qc_match_id_counter', dict(next_id=next_known_match))


async def next_match():
	""" Increase match_id counter, return current match_id """
	counter = await db.select_one(('next_id',), 'qc_match_id_counter')
	await db.update('qc_match_id_counter', dict(next_id=counter['next_id']+1))
	log.debug(f"Current match_id is {counter['next_id']}")
	return counter['next_id']


async def register_match_unranked(ctx, m):
	await db.insert('qc_matches', dict(
		match_id=m.id, channel_id=m.qc.channel.id, queue_id=m.queue.cfg.p_key, queue_name=m.queue.name,
		alpha_name=m.teams[0].name, beta_name=m.teams[1].name,
		at=int(time.time()), ranked=0, winner=None, maps="\n".join(m.maps)
	))

	await db.insert_many('qc_players', (
		dict(channel_id=m.qc.channel.id, user_id=p.id)
		for p in m.players
	), on_dublicate="ignore")

	for p in m.players:
		nick = get_nick(p)
		await db.update(
			"qc_players",
			dict(nick=nick),
			keys=dict(channel_id=m.qc.channel.id, user_id=p.id)
		)

		if p in m.teams[0]:
			team = 0
		elif p in m.teams[1]:
			team = 1
		else:
			team = None

		await db.insert(
			'qc_player_matches',
			dict(match_id=m.id, channel_id=m.qc.channel.id, user_id=p.id, nick=nick, team=team)
		)


async def register_match_ranked(ctx, m):
	await db.insert('qc_matches', dict(
		match_id=m.id, channel_id=m.qc.channel.id, queue_id=m.queue.cfg.p_key, queue_name=m.queue.name,
		alpha_name=m.teams[0].name, beta_name=m.teams[1].name,
		at=int(time.time()), ranked=1, winner=m.winner,
		alpha_score=m.scores[0], beta_score=m.scores[1], maps="\n".join(m.maps)
	))

	for channel_id in {m.qc.id, m.qc.rating.channel_id}:
		await db.insert_many('qc_players', (
			dict(channel_id=channel_id, user_id=p.id, nick=get_nick(p))
			for p in m.players
		), on_dublicate="ignore")

	results = [[
		await m.qc.rating.get_players((p.id for p in m.teams[0])),
		await m.qc.rating.get_players((p.id for p in m.teams[1])),
	]]

	if m.winner is None:  # draw
		after = m.qc.rating.rate(winners=results[0][0], losers=results[0][1], draw=True)
		results.append(after)
	else:  # process actual scores
		n = 0
		while n < m.scores[0] or n < m.scores[1]:
			if n < m.scores[0]:
				after = m.qc.rating.rate(winners=results[-1][0], losers=results[-1][1], draw=False)
				results.append(after)
			if n < m.scores[1]:
				after = m.qc.rating.rate(winners=results[-1][1], losers=results[-1][0], draw=False)
				results.append(after[::-1])
			n += 1

	after = iter_to_dict((*results[-1][0], *results[-1][1]), key='user_id')
	before = iter_to_dict((*results[0][0], *results[0][1]), key='user_id')

	for p in m.players:
		nick = get_nick(p)
		team = 0 if p in m.teams[0] else 1

		await db.update(
			"qc_players",
			dict(
				nick=nick,
				rating=after[p.id]['rating'],
				deviation=after[p.id]['deviation'],
				wins=after[p.id]['wins'],
				losses=after[p.id]['losses'],
				draws=after[p.id]['draws'],
				streak=after[p.id]['streak']
			),
			keys=dict(channel_id=m.qc.rating.channel_id, user_id=p.id)
		)

		await db.insert(
			'qc_player_matches',
			dict(match_id=m.id, channel_id=m.qc.channel.id, user_id=p.id, nick=nick, team=team)
		)
		await db.insert('qc_rating_history', dict(
			channel_id=m.qc.rating.channel_id,
			user_id=p.id,
			at=int(time.time()),
			rating_before=before[p.id]['rating'],
			rating_change=after[p.id]['rating']-before[p.id]['rating'],
			deviation_before=before[p.id]['deviation'],
			deviation_change=after[p.id]['deviation']-before[p.id]['deviation'],
			match_id=m.id,
			reason=m.queue.name
		))

	await m.qc.update_rating_roles(*m.players)
	await m.print_rating_results(ctx, before, after)


async def undo_match(match_id, qc):
	match = await db.select_one(('ranked', 'winner'), 'qc_matches', where=dict(match_id=match_id, channel_id=qc.channel.id))
	if not match:
		return False

	if match['ranked']:
		p_matches = await db.select(('user_id', 'team'), 'qc_player_matches', where=dict(match_id=match_id))
		p_history = iter_to_dict(
			await db.select(
				('user_id', 'rating_change', 'deviation_change'), 'qc_rating_history', where=dict(match_id=match_id)
			), key='user_id'
		)
		stats = iter_to_dict(
			await qc.rating.get_players((p['user_id'] for p in p_matches)), key='user_id'
		)

		for p in p_matches:
			new = stats[p['user_id']]
			changes = p_history[p['user_id']]

			print(match['winner'])
			if match['winner'] is None:
				new['draws'] = max((new['draws'] - 1, 0))
			elif match['winner'] == p['team']:
				new['wins'] = max((new['wins'] - 1, 0))
			else:
				new['losses'] = max((new['losses'] - 1, 0))

			new['rating'] = max((new['rating']-changes['rating_change'], 0))
			new['deviation'] = max((new['deviation']-changes['deviation_change'], 0))

			await db.update("qc_players", new, keys=dict(channel_id=qc.rating.channel_id, user_id=p['user_id']))
		await db.delete("qc_rating_history", where=dict(match_id=match_id))
		members = (qc.channel.guild.get_member(p['user_id']) for p in p_matches)
		await qc.update_rating_roles(*(m for m in members if m is not None))

	await db.delete('qc_player_matches', where=dict(match_id=match_id))
	await db.delete('qc_matches', where=dict(match_id=match_id))
	return True


async def reset_channel(channel_id):
	where = {'channel_id': channel_id}
	await db.delete("qc_players", where=where)
	await db.delete("qc_rating_history", where=where)
	await db.delete("qc_matches", where=where)
	await db.delete("qc_player_matches", where=where)


async def reset_player(channel_id, user_id):
	where = {'channel_id': channel_id, 'user_id': user_id}
	await db.delete("qc_players", where=where)
	await db.delete("qc_rating_history", where=where)
	await db.delete("qc_player_matches", where=where)


async def replace_player(channel_id, user_id1, user_id2, new_nick):
	await db.delete("qc_players", {'channel_id': channel_id, 'user_id': user_id2})
	where = {'channel_id': channel_id, 'user_id': user_id1}
	await db.update("qc_players", {'user_id': user_id2, 'nick': new_nick}, where)
	await db.update("qc_rating_history", {'user_id': user_id2}, where)
	await db.update("qc_player_matches", {'user_id': user_id2}, where)


async def qc_stats(channel_id):
	data = await db.fetchall(
		"SELECT `queue_name`, COUNT(*) as count FROM `qc_matches` WHERE `channel_id`=%s " +
		"GROUP BY `queue_name` ORDER BY count DESC",
		(channel_id,)
	)
	stats = dict(total=sum((i['count'] for i in data)))
	stats['queues'] = data
	return stats


async def user_stats(channel_id, user_id):
	data = await db.fetchall(
		"SELECT `queue_name`, COUNT(*) as count FROM `qc_player_matches` AS pm " +
		"JOIN `qc_matches` AS m ON pm.match_id=m.match_id " +
		"WHERE pm.channel_id=%s AND user_id=%s " +
		"GROUP BY m.queue_name ORDER BY count DESC",
		(channel_id, user_id)
	)
	stats = dict(total=sum((i['count'] for i in data)))
	stats['queues'] = data
	return stats


async def top(channel_id, time_gap=None):
	total = await db.fetchone(
		"SELECT COUNT(*) as count FROM `qc_matches` WHERE channel_id=%s" + (f" AND at>{time_gap} " if time_gap else ""),
		(channel_id, )
	)

	data = await db.fetchall(
		"SELECT p.nick as nick, COUNT(*) as count FROM `qc_player_matches` AS pm " +
		"JOIN `qc_players` AS p ON pm.user_id=p.user_id AND pm.channel_id=p.channel_id " +
		"JOIN `qc_matches` AS m ON pm.match_id=m.match_id " +
		"WHERE pm.channel_id=%s " +
		(f"AND m.at>{time_gap} " if time_gap else "") +
		"GROUP BY p.user_id ORDER BY count DESC LIMIT 10",
		(channel_id, )
	)
	stats = dict(total=total['count'])
	stats['players'] = data
	return stats


async def last_games(channel_id):
	#  get last played ranked match for all players
	data = await db.fetchall(
		"SELECT m.at, p.* FROM `qc_players` AS p " +
		"JOIN qc_matches AS m ON m.match_id=("
		"	SELECT match_id FROM qc_rating_history as h WHERE h.user_id=p.user_id ORDER BY match_id DESC LIMIT 1"
		") " +
		"WHERE p.channel_id=%s AND p.rating IS NOT NULL AND p.deviation IS NOT NULL "
		"GROUP BY p.user_id",
		(channel_id, )
	)
	return data


class StatsJobs:

	def __init__(self):
		self.next_decay_at = int(self.next_monday().timestamp())

	@staticmethod
	def next_monday():
		d = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
		d += datetime.timedelta(days=1)
		while d.weekday() != 0:  # 0 for monday
			d += datetime.timedelta(days=1)
		return d

	@staticmethod
	def tomorrow():
		d = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
		d += datetime.timedelta(days=1)
		return d

	@staticmethod
	async def apply_rating_decays():
		log.info("--- Applying weekly deviation decays ---")
		for qc in bot.queue_channels.values():
			await qc.apply_rating_decay()
			await asyncio.sleep(1)

	async def think(self, frame_time):
		if frame_time > self.next_decay_at:
			self.next_decay_at = int(self.next_monday().timestamp())
			asyncio.create_task(self.apply_rating_decays())


jobs = StatsJobs()
