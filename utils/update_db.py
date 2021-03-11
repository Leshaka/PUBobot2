import sqlite3
import pymysql

SQLITE_FILE = "database.sqlite3"
MYSQL_HOST = "localhost"
MYSQL_USER = "pubobot"
MYSQL_PASS = "pUbOpAAss"
MYSQL_DB = "pubodb"


def dict_factory(cursor, row):
	d = {}
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d


def dict_insert(cursor, table, d):
	qry = "INSERT INTO `{table}` ({keys}) VALUES ({qmarks})".format(
		table=table,
		keys=", ".join((f"`{i}`" for i in d.keys())),
		qmarks=', '.join(('%s' for i in d.keys()))
	)
	cursor.execute(qry, list(d.values()))


def get_value(d1, d2, variable):
	if (val := d1.get(variable)) is None:
		return d2.get(variable)
	return val


def safe_list_get(l, idx, default):
	try:
		return l[idx]
	except IndexError:
		return default

ranks = [
	dict(rank="〈G〉", rating=0, role=None),
	dict(rank="〈F〉", rating=1000, role=None),
	dict(rank="〈E〉", rating=1200, role=None),
	dict(rank="〈D〉", rating=1400, role=None),
	dict(rank="〈C〉", rating=1600, role=None),
	dict(rank="〈B〉", rating=1800, role=None),
	dict(rank="〈A〉", rating=1900, role=None),
	dict(rank="〈★〉", rating=2000, role=None)
]

pick_captains = {
	None: 'no captains',
	0: 'no captains',
	1: 'by role and rating',
	2: 'fair pairs',
	3: 'random'
}
pick_teams = {
	None: 'no teams',
	'no_teams': 'no teams',
	'auto': 'matchmaking',
	'manual': 'draft',
	'random': 'random teams'
}
pq_id = 1

conn1 = sqlite3.connect(SQLITE_FILE)
conn1.row_factory = dict_factory
c1 = conn1.cursor()

conn2 = pymysql.connect(
	host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS, db=MYSQL_DB,
	charset="utf8mb4", autocommit=False, cursorclass=pymysql.cursors.DictCursor
)
c2 = conn2.cursor()

c1.execute("SELECT * FROM channels")
channels = list(c1.fetchall())

progress = 0
for chan in channels:
	progress += 1
	print(f"{progress}/{len(channels)}")

	team_names = chan['team_names'] if chan['team_names'] and len(chan['team_names']) == 2 else "Alpha Beta"
	new_channel = {
		'channel_id': chan['channel_id'],
		'admin_role': chan['admin_role'],
		'moderator_role': chan['moderator_role'],
		'prefix': chan['prefix'],
		'promotion_role': chan['promotion_role'],
		'promotion_delay': chan['promotion_delay'],
		'whitelist_role': chan['whitelist_role'],
		'blacklist_role': chan['blacklist_role'],
		'expire_time': chan['global_expire']
	}
	dict_insert(c2, 'qc_configs', new_channel)
	for rank in ranks:
		dict_insert(c2, 'qc_configs_ranks', {'channel_id': chan['channel_id'], **rank})

	c1.execute("SELECT * FROM pickup_configs WHERE channel_id = ?", (chan['channel_id'], ))
	old_queues = c1.fetchall()
	for queue in old_queues:
		q_team_names = get_value(queue, chan, 'team_names')
		q_team_names = q_team_names if q_team_names and len(q_team_names.split(' ')) == 2 else "Alpha Beta"
		q_team_emojis = get_value(queue, chan, 'team_emojis')
		q_team_emojis = q_team_emojis if q_team_emojis and len(q_team_emojis.split(' ')) == 2 else None
		q_server = get_value(queue, chan, 'ip')
		q_start_msg = get_value(queue, chan, 'startmsg')
		if q_start_msg:
			q_start_msg = q_start_msg.replace("%ip%", q_server or "")
			q_start_msg = q_start_msg.replace("%password%", get_value(queue, chan, 'password') or "")
		new_queue = {
			'channel_id': queue['channel_id'],
			'pq_id': pq_id,
			'name': queue['pickup_name'],
			'size': queue['maxplayers'],
			'ranked': get_value(queue, chan, 'ranked'),
			'promotion_role': get_value(queue, chan, 'promotion_role'),
			'is_default': 1 if chan['++_req_players'] and chan['++_req_players'] <= queue['maxplayers'] else 0,
			'captains_role': get_value(queue, chan, 'captains_role'),
			'start_msg': q_start_msg[:1000] if q_start_msg else None,
			'server': q_server[:100].strip("`") if q_server else None,
			'pick_captains': pick_captains[get_value(queue, chan, 'pick_captains')],
			'pick_teams': pick_teams[get_value(queue, chan, 'pick_teams')],
			'pick_order': queue['pick_order'],
			'team_names': q_team_names,
			'team_emojis': q_team_emojis,
			'check_in_timeout': get_value(queue, chan, 'require_ready'),
			'blacklist_role': queue['blacklist_role'],
			'whitelist_role': queue['whitelist_role'],
			'autostart': bool(get_value(queue, chan, 'autostart'))
		}
		dict_insert(c2, 'pq_configs', new_queue)
		pq_id += 1

	c1.execute("SELECT * FROM channel_players WHERE channel_id = ?", (chan['channel_id'], ))
	old_players = c1.fetchall()
	for player in old_players:
		rating = max(player['rank'], 0) if player['rank'] else player['rank']
		deviation = 300 - (10 * (min(15, int(player['wins'] or 0) + int(player['loses'] or 0))))
		new_player = {
			'channel_id': player['channel_id'],
			'user_id': player['user_id'],
			'nick': player['nick'] or 'None',
			'rating': rating,
			'deviation': deviation,
			'wins': player['wins'] or 0,
			'losses': player['loses'] or 0,
		}
		dict_insert(c2, 'qc_players', new_player)

	c1.execute("SELECT * FROM pickups WHERE channel_id = ?", (chan['channel_id'], ))
	old_pickups = c1.fetchall()
	for pickup in old_pickups:
		new_match = {
			'match_id': pickup['pickup_id'],
			'channel_id': pickup['channel_id'],
			'queue_name': pickup['pickup_name'],
			'at': pickup['at'],
			'alpha_name': team_names.split(" ")[0],
			'beta_name': team_names.split(" ")[1],
			'ranked': 0
		}
		dict_insert(c2, 'qc_matches', new_match)

	c1.execute("SELECT * FROM player_pickups WHERE channel_id = ?", (chan['channel_id'], ))
	old_records = c1.fetchall()
	for record in old_records:
		if record['pickup_id']:
			new_record = {
				'match_id': record['pickup_id'] or 0,
				'channel_id': record['channel_id'],
				'user_id': record['user_id'],
				'nick': record['user_name'] or 'None',
				'team': None
			}
			dict_insert(c2, 'qc_player_matches', new_record)

conn2.commit()
conn1.close()
conn2.close()
