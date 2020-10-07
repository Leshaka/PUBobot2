# -*- coding: utf-8 -*-
from types import SimpleNamespace
import re
import emoji

from core.database import db
from core.utils import format_emoji
from core.console import log


class ConfigSpawner:
	""" This class contains CfgFactory objects and spawns CfgCollection objects """

	def __init__(self, pkeys, prefix=''):
		self.prefix = prefix
		self.pkeys = pkeys

		self.spawned_pkeys = []
		self.factories = dict()

	def add_factory(self, name, variables=[], **kwargs):
		name = self.prefix + name
		if name in self.factories.keys():
			raise(KeyError('Config factory with this name already exists'))

		cfg_factory = CfgFactory(name, variables=variables, **kwargs)
		db.ensure_table(dict(
			tname=cfg_factory.table,
			columns=[
				*self.pkeys,
				*(dict(cname=v.name, ctype=v.ctype, default=v.default) for v in variables)
			],
			primary_keys=[pk['cname'] for pk in self.pkeys]
		))
		for var_table in cfg_factory.tables.values():
			var_table.table = 'vt_' + name + '_' + var_table.name
			db.ensure_table(dict(
				tname=var_table.table,
				columns=[
					dict(cname='guild_id', ctype=db.types.str, notnull=True),
					*(dict(cname=v.name, ctype=v.ctype, default=v.default) for v in var_table.variables.values())
				]
			))
		self.factories[name] = cfg_factory

	async def new(self, pkeys, guild):
		if pkeys in self.spawned_pkeys:
			raise(ValueError('Already spawned config collection with given pkeys'))

		cfg_collection = SimpleNamespace()
		cfg_collection._guild = guild
		for cfgFactory in self.factories.values():
			cfg = Config(guild, cfgFactory)
			await cfg._load()
			cfg_collection.__setattr__(cfgFactory.name, cfg)
			if cfgFactory.on_new:
				cfgFactory.on_new(cfg_collection)

		self.spawned_pkeys.append(pkeys)
		return cfg_collection


class CfgFactory:

	def __init__(self, name, variables=[], tables=[], display=None, icon='star.png', on_new=None):
		self.name = name
		self.display = display or name
		self.icon = icon
		self.table = 'configs_' + name
		self.variables = {v.name: v for v in variables}
		self.tables = {t.name: t for t in tables}
		self.configs = dict()
		self._row_blank = {v.name: v.default for v in variables}
		self.on_new = on_new


class Config:

	def __init__(self, guild, cfg_factory):
		self._guild = guild
		self._factory = cfg_factory
		self._values = dict(**self._factory._row_blank)
		self._tables = SimpleNamespace()

	async def _load(self):
		row = await db.select_one(['*'], self._factory.table, {'guild_id': self._guild.id})
		if not row:
			# Insert blank row if existing not found
			row = {'guild_id': self._guild.id, **self._values}
			await db.insert(self._factory.table, row)

		# generate useful objects from variables values and set it as attributes
		row.pop('guild_id')
		for var_name in self._factory.variables.keys():
			try:
				setattr(self, var_name, await self._factory.variables[var_name].wrap(row[var_name], self._guild))
			except Exception as e:
				log.error("Failed to wrap variable '{}': {}".format(var_name, str(e)))
				setattr(self, var_name, await self._factory.variables[var_name].wrap(None, self._guild))

		for var_table in self._factory.tables.values():
			rows = await db.select(['*'], var_table.table, {'guild_id': self._guild.id})
			l = []
			for row in rows:
				try:
					l.append(await var_table.wrap_row(row, self._guild))
				except Exception as e:
					log.error("Failed to wrap a table row from '{}': {}".format(var_table.name, str(e)))
			setattr(self._tables, var_table.name, l)

	async def _update_db(self, d):
		await db.update(self._factory.table, d, {'guild_id': self._guild.id})

	async def update(self, d):
		print(d)
		tables = d.pop('_tables') if '_tables' in d.keys() else {}
		print(tables)
		v_validated = dict()
		t_validated = dict()

		# validate strings and convert to database-friendly objects
		for var_name in d.keys():
			if var_name not in self._factory.variables.keys():
				raise(KeyError("Variable '{}' not found.".format(var_name)))
			v_validated[var_name] = await self._factory.variables[var_name].validate(d[var_name], self._guild)
		for tname in tables.keys():
			if tname not in self._factory.tables.keys():
				raise (KeyError("Table '{}' not found.".format(tname)))
			t_validated[tname] = await self._factory.tables[tname].validate(tables[tname], self._guild)

		# Update db and wrap to variables
		await self._update_db(v_validated)
		self._values.update(v_validated)
		# update useful objects
		for var_name in v_validated.keys():
			setattr(self, var_name, await self._factory.variables[var_name].wrap(v_validated[var_name], self._guild))
			if self._factory.variables[var_name].on_change:
				self._factory.variables[var_name].on_change(self._guild.cfg)

		for tname in t_validated.keys():
			table = self._factory.tables[tname]
			await self._update_table_db(table, t_validated[tname])
			setattr(self._tables, tname, await table.wrap(t_validated[tname], self._guild))

	async def _update_table_db(self, table, l):
		await db.delete(table.table, where={'guild_id': self._guild.id})
		await db.insert_many(table.table, (dict(guild_id=self._guild.id, **d) for d in l))

	async def set(self, var_name, string):
		value = await self._factory.variables[var_name].validate(string, self._guild)
		await db.update(self._factory.table, {var_name: value}, {'guild_id': self._guild.id})
		self._values[var_name] = value
		setattr(self, var_name, await self._factory.variables[var_name].wrap(value, self._guild))
		if self._factory.variables[var_name].on_change:
			self._factory.variables[var_name].on_change(self._guild.cfg)


class Variable:
	""" Variable base class """

	def __init__(self, name, default=None, display=None, description=None, notnull=False, on_change=None):
		self.name = name
		self.default = default
		self.display = display or name
		self.description = description
		self.notnull = notnull
		self.on_change = on_change

	async def validate(self, string, guild):
		""" Validate and return database-friendly object from received string """
		return string

	async def wrap(self, value, guild):
		""" Return useful objects like role from role_id string etc """
		return value

	def readable(self, obj):
		""" returns string from a useful object"""
		return str(obj) if obj is not None else None


class StrVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.str


class EmojiVar(Variable):
	# Returns unicode emoji or a guild's custom emoji string

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.str

	async def validate(self, string, guild):
		if string is None:
			return None

		if re.match("^:[^ ]*:$", string):
			return format_emoji(string.strip(':'), guild) or emoji.emojize(string, use_aliases=True)
		else:
			return string


class TextVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.text


class OptionVar(Variable):

	def __init__(self, name, options, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.str
		self.options = options

	async def validate(self, string, guild):
		if string is None:
			return None

		if string in self.options:
			return string
		raise ValueError('Specified value not in options list.')


class BoolVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		# 0 == False and 1 == True in python
		value = value.lower()
		if value in ['1', 'on', 'true']:
			return 1
		elif value in ['0', 'off', 'false']:
			return 0
		elif value is None:
			return None
		raise(ValueError('{} value must be set to 0 or 1 or None'.format(self.name)))

	def readable(self, obj):
		if obj is not None:
			return 'on' if obj else 'off'
		return None


class IntVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		if value is None:
			return None
		return int(value)


class RoleVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		if value is None:
			return None

		mention = re.match('^<@&([0-9]+)>$', value)
		if mention:
			role_id = int(mention.group(1))
			if not guild.get_role(role_id):
				raise ValueError("User '{}' not found on the dc guild.".format(value))

		else:
			try:
				role_id = next((role for role in guild.roles if role.name == value or str(role.id) == value)).id
			except StopIteration:
				raise ValueError("User '{}' not found on the dc guild.".format(value))

		return role_id

	async def wrap(self, value, guild):
		if value:
			role = guild.get_role(value)
			if role:
				return role
			else:
				raise ValueError("Requested role for variable '{}' not found on the guild".format(self.name))

	def readable(self, obj):
		if obj:
			return obj.name
		else:
			return None


class MemberVar(Variable):

	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		if value is None:
			return None

		mention = re.match("^<@[!]*([0-9]+)>$", value)
		if mention:
			user_id = int(mention.group(1))
			if not guild.get_member(user_id):
				raise ValueError("User '{}' not found on the guild.".format(value))

		else:
			value = value.lower()
			try:
				user_id = next((member for member in guild.members if
					(member.nick or member.name).lower() == value or str(member.id) == value
				))
			except StopIteration:
				raise ValueError("User '{}' not found on the guild.".format(value))

		return user_id

	async def wrap(self, value, guild):
		if value:
			member = guild.get_member(value)
			if member:
				return member
			else:
				raise ValueError("Requested user for variable '{}' not found on the guild.".format(self.name))

	def readable(self, obj):
		if obj:
			return obj.name + "#" + obj.discriminator
		else:
			return None


class TextChanVar(Variable):
	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		if value is None:
			return None

		mention = re.match("^<#([0-9]+)>$", value)
		if mention:
			channel_id = int(mention.group(1))
			if not guild.get_channel(channel_id):
				raise ValueError("Channel '{}' not found on the dc guild.".format(value))

		else:
			try:
				channel_id = next((channel for channel in guild.channels if
					channel.name == value.lstrip('#') or str(channel.id) == value
				)).id
			except StopIteration:
				raise ValueError("Channel '{}' not found on the guild.".format(value))

		return channel_id

	async def wrap(self, value, guild):
		if value:
			channel = guild.get_channel(value)
			if channel:
				return channel
			else:
				raise ValueError("Requested channel for variable '{}' not found on the guild.".format(self.name))

	def readable(self, obj):
		if obj:
			return "#" + obj.name
		else:
			return None


class VariableTable:

	def __init__(self, name, variables=[], display=None, blank=None, default=[], description=None, on_change=None):
		self.name = name
		self.table = 'variable_'+name
		self.variables = {v.name: v for v in variables}
		self.display = display or name
		self.blank = blank if blank else {i: None for i in self.variables.keys()}
		self.default = default
		self.description = description
		self.on_change = on_change

	async def validate(self, l, guild):
		if type(l) != list:
			raise (ValueError('Value must be a list.'))

		values = []
		for d in l:
			if d.keys() != self.variables.keys():
				raise(ValueError('Incorrect table columns.'))
			validated = {var_name: await self.variables[var_name].validate(value, guild) for var_name, value in d.items()}
			values.append(validated)
		return values

	async def wrap(self, l, guild):
		wrapped = []
		for d in l:
			wrapped.append({var_name: await self.variables[var_name].wrap(value, guild) for var_name, value in d.items()})
		return wrapped

	async def wrap_row(self, d, guild):
		return {var_name: await self.variables[var_name].wrap(value, guild) for var_name, value in d.items() if var_name != 'guild_id'}

	def readable(self, l):
		return [{var_name: self.variables[var_name].readable(value) for var_name, value in d.items()} for d in l]

	def readable_row(self, d):
		return {var_name: self.variables[var_name].readable(value) for var_name, value in d.items()}


class Variables:
	StrVar = StrVar
	EmojiVar = EmojiVar
	TextVar = TextVar
	OptionVar = OptionVar
	BoolVar = BoolVar
	IntVar = IntVar
	RoleVar = RoleVar
	TextChanVar = TextChanVar
