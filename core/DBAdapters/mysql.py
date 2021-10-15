# -*- coding: utf-8 -*-
import aiomysql
from pymysql import err as mysqlErr
from .common import *

from core.console import log


class Types:
	bool = "TINYINT(1)"
	int = "BIGINT"
	float = "FLOAT"
	str = "VARCHAR(191)"
	text = "VARCHAR(2000)"


reference_options = dict(
	RESTRICT='RESTRICT',
	CASCADE='CASCADE',
	SET_NULL='SET NULL',
	SET_DEFAULT='SET DEFAULT'
)

table_blank = dict(tname=None, columns=[], primary_keys=[], foreign_keys=[])
column_blank = dict(cname=None, ctype=Types.str, notnull=False, unique=False, autoincrement=False, default=None)
fkey_blank = dict(cname=None, refTable=None, refColumn=None, on_delete=None, on_update=None)


class Adapter:
	types = Types
	errors = Errors

	def __init__(self, db_address, loop):
		self.dbAddress = db_address
		self.loop = loop
		try: 
			self.dbUser, db_address = db_address.split(':', 1)
			self.dbPassword, db_address = db_address.split('@', 1)
			self.dbHost, self.dbName = db_address.split('/', 1)
			if self.dbHost.find(':') > -1:
				self.dbHost, self.dbPort = self.dbHost.split(':')
			else:
				self.dbPort = '3306'
		except Exception:
			raise(ValueError('Bad database address string: ' + self.dbAddress))

		try:
			self.pool = self.loop.run_until_complete(aiomysql.create_pool(
				host=self.dbHost,
				user=self.dbUser,
				password=self.dbPassword,
				db=self.dbName,
				charset='utf8mb4',
				autocommit=True,
				cursorclass=aiomysql.cursors.DictCursor))

		except mysqlErr.Error as e:
			self.wrap_exc(e)

	async def execute(self, *args):
		async with self.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute(*args)
				except Exception as e:
					self.wrap_exc(e)

	async def executemany(self, *args):
		async with self.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.executemany(*args)
				except mysqlErr.Error as e:
					self.wrap_exc(e)

	async def fetchone(self, *args):
		async with self.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute(*args)
					return await cur.fetchone()
				except mysqlErr.Error as e:
					self.wrap_exc(e)

	async def fetchall(self, *args):
		async with self.pool.acquire() as conn:
			async with conn.cursor() as cur:
				try:
					await cur.execute(*args)
					return await cur.fetchall()
				except mysqlErr.Error as e:
					self.wrap_exc(e)

	@staticmethod
	def _mysql_column(kwargs):
		return "`{cname}` {ctype}{notnull}{unique}{autoincrement}{default}".format(
			cname=kwargs['cname'],
			ctype=kwargs['ctype'],
			notnull=" NOT NULL" if kwargs['notnull'] else "",
			unique=" UNIQUE" if kwargs['unique'] else "",
			autoincrement=" AUTO_INCREMENT" if kwargs['autoincrement'] else "",
			default=" DEFAULT '{}'".format(kwargs['default']) if kwargs['default'] is not None else ""
		)

	@staticmethod
	def _mysql_fkey(kwargs):
		return "({cname}) REFERENCES {refTable}({refColumn}){on_delete}{on_update}".format(
			cname=kwargs['cname'],
			refTable=kwargs['refTable'],
			refColumn=kwargs['refColumn'],
			on_delete=" ON DELETE " + reference_options[kwargs['on_delete']] if kwargs['on_delete'] else '',
			on_update=" ON UPDATE " + reference_options[kwargs['on_update']] if kwargs['on_update'] else ''
		)

	@staticmethod
	def _mysql_insert(columns, table, on_dublicate):
		return "{action}{ignore} INTO {table} ({columns}) VALUES({values})".format(
			action="REPLACE" if on_dublicate == 'replace' else "INSERT",
			ignore=" IGNORE" if on_dublicate == 'ignore' else "",
			table=table,
			columns=", ".join((f"`{i}`" for i in columns)),
			values=", ".join(('%s' for i in range(len(columns))))
		)

	@staticmethod
	def _mysql_update(table, columns, keys):
		return "UPDATE {table} SET {columns} WHERE {keys}".format(
			table=table,
			columns=",".join(["`{}`=%s".format(i) for i in columns]),
			keys=" AND ".join(["`{}`=%s".format(i) for i in keys])
		)

	async def create_table(self, table):
		table = {**table_blank, **table}

		columns = [self._mysql_column({**column_blank, **col}) for col in table['columns']]
		fkeys = ["FOREIGN KEY " + self._mysql_fkey({**fkey_blank, **fkey}) for fkey in table['foreign_keys']]
		pkeys = ", PRIMARY KEY(" + ", ".join(table['primary_keys']) + ')' if len(table['primary_keys']) else ''

		request = "CREATE TABLE {tname} ({tdeskr})".format(
			tname=table['tname'],
			tdeskr=", ".join((columns + fkeys)) + pkeys
		)

		await self.execute(request)

	def ensure_table(self, table):
		self.loop.run_until_complete(self._ensure_table(table))

	async def _ensure_table(self, table):
		table = {**table_blank, **table}
		columns = await self.fetchall(
			"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(table['tname'])
		)
		columns = {i['COLUMN_NAME']: i['DATA_TYPE'] for i in columns}

		# Create table if not exist
		if not len(columns):
			await self.create_table(table)
			return

		# Create columns if not exist
		for col in table['columns']:
			col = {**column_blank, **col}
			if col['cname'] not in columns.keys():
				await self.execute("ALTER TABLE {tname} ADD COLUMN {column_sql}".format(
					tname=table['tname'],
					column_sql=self._mysql_column({**column_blank, **col})
				))
				# Add a foreign key if needed
				for fkey in (fkey for fkey in table['foreign_keys'] if fkey['cname'] == col['cname']):
					await self.execute("ALTER TABLE {tname} ADD FOREIGN KEY {fkey_sql}".format(
						tname=table['tname'],
						fkey_sql=self._mysql_fkey({**fkey_blank, **fkey})
					))
			elif not col['ctype'].lower().startswith(columns[col['cname']]):
				raise(TypeError(
					"Column '{}' types are mismatching, {} and {}".format(col['cname'], col['ctype'], columns[col['cname']])
				))

	async def select(self, columns, table, where=None, order_by=None, order_asc=False, limit=None, one=False):
		conditions = " WHERE " + " AND ".join(("`{}`=%s".format(k) for k in where.keys())) if where else ''
		args = list(where.values()) if where else ()

		# fix queries where there are some restricted words, for example in MySQL 8 'rank' is restricred
		sql_restricted_words = [
				'rank',
				'role',
		]
		parsed_columns = []
		for column in columns:
			if column in sql_restricted_words:
				parsed_columns.append('`{}`'.format(column))
			else:
				parsed_columns.append(column)

		request = "SELECT {columns} FROM `{table}`{where}{order}{limit}".format(
			columns=', '.join(columns),
			table=table,
			where=conditions,
			order=" ORDER BY "+order_by+(" ASC" if order_asc else " DESC") if order_by else "",
			limit=(" LIMIT " + str(limit)) if limit else ""
		)

		if one:
			return await self.fetchone(request, args)
		else:
			return await self.fetchall(request, args)

	async def select_one(self, *args, **kwargs):
		return await self.select(*args, **kwargs, one=True)

	async def delete(self, table, where=None):
		conditions = " WHERE " + " AND ".join(("`{}`=%s".format(k) for k in where.keys())) if where else ''
		args = list(where.values()) if where else ()
		await self.execute("DELETE FROM {}{}".format(table, conditions), args)

	async def insert(self, table, d, on_dublicate=None):
		request = self._mysql_insert(d.keys(), table, on_dublicate)
		await self.execute(request, list(d.values()))

	async def update(self, table, d, keys):
		request = self._mysql_update(table, d.keys(), keys.keys())
		await self.execute(request, list(d.values()) + list(keys.values()))

	async def insert_many(self, table, it, on_dublicate=None):
		try:
			first, it = peek(iter(it))
		except StopIteration:
			return

		request = self._mysql_insert(first.keys(), table, on_dublicate)
		await self.executemany(request, (list(d.values()) for d in it))

	async def close(self):
		self.pool.close()
		await self.pool.wait_closed()

	@staticmethod
	def wrap_exc(e):
		if e.__class__ in [mysqlErr.InternalError, mysqlErr.OperationalError]:
			raise OperationalError() from e

		elif e.__class__ == mysqlErr.DataError:
			raise DataError() from e

		elif e.__class__ == mysqlErr.IntegrityError:
			raise IntegrityError() from e

		elif e.__class__ == mysqlErr.ProgrammingError:
			raise ProgrammingError() from e

		else:
			raise DatabaseError() from e
