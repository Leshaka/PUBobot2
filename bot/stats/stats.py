# -*- coding: utf-8 -*-
import time
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
		dict(cname="draws", ctype=db.types.int, notnull=True, default=0)
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
		dict(cname="maps", ctype=db.types.str)
	],
	primary_keys=["match_id"]
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


async def last_match_id():
	m = await db.select_one(('match_id',), 'qc_matches', order_by='match_id', limit=1)
	print(m)
	return m['match_id'] if m else 0


async def register_match_unranked(m):
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


async def register_match_ranked(m):
	await db.insert('qc_matches', dict(
		match_id=m.id, channel_id=m.qc.channel.id, queue_id=m.queue.cfg.p_key, queue_name=m.queue.name,
		alpha_name=m.teams[0].name, beta_name=m.teams[1].name,
		at=int(time.time()), ranked=1, winner=m.winner, maps="\n".join(m.maps)
	))

	await db.insert_many('qc_players', (
		dict(channel_id=m.qc.channel.id, user_id=p.id)
		for p in m.players
	), on_dublicate="ignore")

	before = [
		await m.qc.rating.get_players((p.id for p in m.teams[0])),
		await m.qc.rating.get_players((p.id for p in m.teams[1])),
	]

	after = m.qc.rating.rate(
		winners=before[m.winner or 0],
		losers=before[abs((m.winner or 0)-1)],
		draw=m.winner is None
	)

	after = iter_to_dict(after, key='user_id')
	before = iter_to_dict((*before[0], *before[1]), key='user_id')

	for p in m.players:
		nick = get_nick(p)
		team = 0 if p in m.teams[0] else 1

		if m.winner is None:
			after[p.id]['draws'] += 1
		elif m.winner == team:
			after[p.id]['wins'] += 1
		else:
			after[p.id]['losses'] += 1

		await db.update(
			"qc_players",
			dict(
				nick=nick,
				rating=after[p.id]['rating'],
				deviation=after[p.id]['deviation'],
				wins=after[p.id]['wins'],
				losses=after[p.id]['losses'],
				draws=after[p.id]['draws']
			),
			keys=dict(channel_id=m.qc.channel.id, user_id=p.id)
		)

		await db.insert(
			'qc_player_matches',
			dict(match_id=m.id, channel_id=m.qc.channel.id, user_id=p.id, nick=nick, team=team)
		)
		await db.insert('qc_rating_history', dict(
			channel_id=m.qc.channel.id,
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
	await m.print_rating_results(before, after)


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

			await db.update("qc_players", new, keys=dict(channel_id=qc.channel.id, user_id=p['user_id']))
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
	where = {'channel_id': channel_id, 'user_id': user_id1}
	update = {'user_id': user_id2}
	await db.update("qc_players", {'user_id': user_id2, 'nick': new_nick}, where)
	await db.update("qc_rating_history", {'user_id': user_id2}, where)
	await db.update("qc_player_matches", {'user_id': user_id2}, where)
