# -*- coding: utf-8 -*-
from asyncio import get_event_loop
from importlib import import_module
from core.config import cfg


def init_db(db_uri):
	db_type, db_address = db_uri.split("://", 1)
	adapter = import_module('core.DBAdapters.' + db_type)
	return adapter.Adapter(db_address)


db = init_db(cfg.DB_URI)
