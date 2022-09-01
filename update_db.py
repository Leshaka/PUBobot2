#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

if input("Please backup your database before proceeding. Type 'y' to confirm:").lower() != 'y':
	raise ValueError('Aborted')

from core.console import log
from core.database import db


log.loglevel = 0


db.ensure_table(dict(
	tname='qc_configs',
	columns=[
		dict(cname='channel_id', ctype=db.types.int, notnull=True),
		dict(cname='factory_version', ctype=db.types.int),
		dict(cname='cfg_name', ctype=db.types.str),
		dict(cname='cfg_info', ctype=db.types.text, default="{}"),
		dict(cname='cfg_data', ctype=db.types.dict, default="{}")
	],
	primary_keys=['channel_id']
))

db.ensure_table(dict(
	tname='pq_configs',
	columns=[
		dict(cname='pq_id', ctype=db.types.int, notnull=True),
		dict(cname='channel_id', ctype=db.types.int),
		dict(cname='factory_version', ctype=db.types.int),
		dict(cname='cfg_name', ctype=db.types.str),
		dict(cname='cfg_info', ctype=db.types.text, default="{}"),
		dict(cname='cfg_data', ctype=db.types.dict, default="{}")
	],
	primary_keys=['pq_id']
))


async def main():
	config = None
	qc_cfgs = await db.select(['*'], 'qc_configs')
	for qc in qc_cfgs:
		config = {name: val for name, val in qc.items() if name not in ['factory_version', 'channel_id', 'cfg_name', 'cfg_info', 'cfg_data']}
		ranks = await db.select(['rank', 'rating', 'role'], 'qc_configs_ranks', where={'channel_id': qc['channel_id']})
		config['ranks'] = ranks
		await db.update(
			'qc_configs', {'factory_version': 1, 'cfg_name': 'qc_config', 'cfg_data': json.dumps(config)},
			{'channel_id': qc['channel_id']}
		)
	if config:
		for name in config.keys():
			log.info(f'DROPPING COLUMN `{name}` in `qc_configs`...')
			await db.execute(f'ALTER TABLE qc_configs DROP COLUMN `{name}`')
			await db.execute(f'ALTER TABLE qc_configs CHANGE channel_id channel_id bigint(20) AUTO_INCREMENT')

	config = None
	pq_cfgs = await db.select(['*'], 'pq_configs')
	for pq in pq_cfgs:
		config = {name: val for name, val in pq.items() if name not in ['factory_version', 'pq_id', 'channel_id', 'cfg_name', 'cfg_info', 'cfg_data']}
		aliases = await db.select(['alias'], 'pq_configs_aliases', where={'pq_id': pq['pq_id']})
		maps = await db.select(['name'], 'pq_configs_maps', where={'pq_id': pq['pq_id']})
		config['aliases'] = aliases
		config['maps'] = maps
		await db.update(
			'pq_configs', {'factory_version': 1, 'cfg_name': 'pq_config', 'cfg_data': json.dumps(config)},
			{'pq_id': pq['pq_id']}
		)
	if config:
		for name in config.keys():
			log.info(f'DROPPING COLUMN `{name}` in `pq_configs`...')
			await db.execute(f'ALTER TABLE pq_configs DROP COLUMN `{name}`')
			await db.execute(f'ALTER TABLE pq_configs CHANGE pq_id pq_id bigint(20) AUTO_INCREMENT')

db.loop.run_until_complete(main())
