# -*- coding: utf-8 -*-
from types import SimpleNamespace
import re
import emoji
from datetime import datetime

from core.database import db
from core.utils import format_emoji, parse_duration, seconds_to_str
from core.console import log


class CfgFactory:

	def __init__(self, name, p_key, f_key=None, variables=[], tables=[], display=None, icon='star.png'):
		self.p_key = p_key
		self.f_key = f_key
		self.keys = [dict(cname=p_key, ctype=db.types.int, notnull=True)]
		if f_key:
			self.keys.append(dict(cname=f_key, ctype=db.types.int))
		self.name = name
		self.display = display or name
		self.icon = icon
		self.table = name
		self.variables = {v.name: v for v in variables}
		self.tables = {t.name: t for t in tables}
		self.row_blank = {v.name: v.default for v in self.variables.values()}

		db.ensure_table(dict(
			tname=self.table,
			columns=[
				*self.keys,
				*(dict(cname=v.name, ctype=v.ctype, default=v.default) for v in variables)
			],
			primary_keys=[self.p_key]
		))

		for var_table in self.tables.values():
			var_table.table = self.name + '_' + var_table.name
			db.ensure_table(dict(
				tname=var_table.table,
				columns=[
					*self.keys,
					*(dict(cname=v.name, ctype=v.ctype, default=v.default) for v in var_table.variables.values())
				]
			))

	async def spawn(self, guild, p_key=None, f_key=None):
		""" Load existing Config from db by given p_key if exists or spawn a new one """

		row = await db.select_one(['*'], self.table, {self.p_key: p_key})
		if row:
			return await Config.load(self, row, guild)
		else:
			row = {v.name: v.default for v in self.variables.values()}
			row[self.p_key] = p_key if p_key else await self.get_max(self.p_key)+1
			if f_key:
				row[self.f_key] = f_key

			await db.insert(self.table, row)

			for var_table in self.tables.values():
				if var_table.default:
					await db.insert_many(var_table.table, [{self.p_key: p_key, **row} for row in var_table.default])

			return await Config.load(self, row, guild)

	async def select(self, guild, keys):
		""" Returns all Config objects from db by given keys """

		rows = await db.select(['*'], self.table, keys)
		return [await Config.load(self, row, guild) for row in rows]

	async def p_keys(self):
		""" Return all existing p_keys in the database """

		return [row[self.p_key] for row in await db.select([self.p_key], self.table)]

	async def get_max(self, key):
		""" Return max value for given column """

		data = await db.select_one([key], self.table, order_by=key, limit=1)
		return data.get(key) if data else 0


class Config:

	@classmethod
	async def load(cls, cfg_factory, row, guild):
		self = Config(cfg_factory, row, guild)

		# Wrap database data into useful objects and update self attributes
		for var in self._factory.variables.values():
			try:
				obj = await var.wrap(row[var.name], self._guild)
			except Exception as e:
				log.error("Failed to wrap variable '{}': {}".format(var.name, str(e)))
				obj = await var.wrap(var.default, self._guild)
			setattr(self, var.name, obj)

		for table in self._factory.tables.values():
			objects = []
			for row in await db.select(table.variables.keys(), table.table, {self._factory.p_key: self.p_key}):
				try:
					objects.append(await table.wrap_row(row, self._guild))
				except Exception as e:
					log.error("Failed to wrap a table row '{}' from '{}': {}".format(row, table.name, str(e)))
			setattr(self.tables, table.name, objects)

		return self

	def __init__(self, cfg_factory, row, guild):
		self._guild = guild
		self._factory = cfg_factory
		self.p_key = row.pop(cfg_factory.p_key)
		self.f_key = row.pop(cfg_factory.f_key) if cfg_factory.f_key else None
		self.tables = SimpleNamespace()

	async def update(self, data):
		tables = data.pop('tables') if 'tables' in data.keys() else {}

		print(data)
		objects = dict()
		table_objects = dict()
		# Validate data
		for key, value in data.items():
			if key not in self._factory.variables.keys():
				raise KeyError("Variable '{}' not found.".format(key))
			vo = self._factory.variables[key]
			data[key] = await vo.validate(value, self._guild)
			objects[key] = await vo.wrap(data[key], self._guild)
			vo.verify(objects[key])

		for key, value in tables.items():
			if key not in self._factory.tables.keys():
				raise KeyError("Table '{}' not found.".format(key))
			vo = self._factory.tables[key]
			tables[key] = await vo.validate(value, self._guild)
			table_objects[key] = await vo.wrap(tables[key], self._guild)
			vo.verify(table_objects[key])

		# Update useful objects and push to database
		if len(data):
			for key, value in data.items():
				vo = self._factory.variables[key]
				setattr(self, key, objects[key])
				if vo.on_change:
					vo.on_change(self)
			await db.update(self._factory.table, data, {self._factory.p_key: self.p_key})

		for key, value in tables.items():
			vo = self._factory.tables[key]
			setattr(self.tables, key, await vo.wrap(value, self._guild))
			await db.delete(vo.table, where={self._factory.p_key: self.p_key})
			for row in value:
				await db.insert(vo.table, {self._factory.p_key: self.p_key, **row})

	def to_json(self):
		data = {key: value.readable(getattr(self, key)) for key, value in self._factory.variables.items()}
		data["tables"] = dict()
		for key, value in self._factory.tables.items():
			data["tables"][key] = value.readable(getattr(self.tables, key))
		return data


class Variable:
	""" Variable base class """

	def __init__(
			self, name, default=None, display=None, description=None,
			notnull=False, on_change=None, verify=None, verify_message=None
	):
		self.name = name
		self.default = default
		self.display = display or name
		self.description = description
		self.notnull = notnull
		self.on_change = on_change
		self.verify_f = verify or (lambda x: True)
		self.verify_message = verify_message

	async def validate(self, string, guild):
		""" Validate and return database-friendly object from received string """
		return string

	async def wrap(self, value, guild):
		""" Return useful objects like role from role_id string etc """
		return value

	def readable(self, obj):
		""" returns string from a useful object"""
		return str(obj) if obj is not None else None

	def verify(self, obj):
		""" optional verification of generated object """
		if obj and not self.verify_f(obj):
			raise(VerifyError(message=self.verify_message))


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
		if value is None:
			return None
		value = value.lower()
		if value in ['1', 'on', 'true']:
			return 1
		elif value in ['0', 'off', 'false']:
			return 0
		raise (ValueError('{} value must be set to 0 or 1 or None'.format(self.name)))

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


class DurationVar(Variable):
	def __init__(self, name, **kwargs):
		super().__init__(name, **kwargs)
		self.ctype = db.types.int

	async def validate(self, value, guild):
		if value is None:
			return None

		if re.match(r"^\d\d:\d\d:\d\d$", value):
			x = sum(x * int(t) for x, t in zip([3600, 60, 1], value.split(":")))
			print(x)
			return x
		try:
			return parse_duration(value)
		except ValueError:
			raise ValueError("Invalid duration format.")

	async def wrap(self, value, guild):
		return value

	def readable(self, obj):
		if obj:
			return seconds_to_str(obj)
		else:
			return None


class VariableTable:

	def __init__(self, name, variables=[], display=None, blank=None, default=[], description=None, on_change=None):
		self.name = name
		self.table = 'variable_' + name
		self.variables = {v.name: v for v in variables}
		self.display = display or name
		self.blank = blank if blank else {i: None for i in self.variables.keys()}
		self.default = default
		self.description = description
		self.on_change = on_change

	async def validate(self, data, guild):
		if type(data) != list:
			raise (ValueError('Value must be a list.'))

		validated = []
		for row in data:
			if row.keys() != self.variables.keys():
				raise (ValueError(f"Incorrect columns for table {self.name}."))
			validated.append(
				{var_name: await self.variables[var_name].validate(value, guild) for var_name, value in row.items()}
			)
		return validated

	async def wrap(self, data, guild):
		wrapped = []
		for row in data:
			wrapped.append(
				{var_name: await self.variables[var_name].wrap(value, guild) for var_name, value in row.items()})
		return wrapped

	async def wrap_row(self, d, guild):
		return {var_name: await self.variables[var_name].wrap(value, guild) for var_name, value in d.items()}

	def readable(self, l):
		return [{var_name: self.variables[var_name].readable(value) for var_name, value in d.items()} for d in l]

	def readable_row(self, d):
		return {var_name: self.variables[var_name].readable(value) for var_name, value in d.items()}

	def verify(self, l):
		return(
			all((
				all((self.variables[key].verify(value) for key, value in d.items())) for d in l
			))
		)


class Variables:
	StrVar = StrVar
	EmojiVar = EmojiVar
	TextVar = TextVar
	OptionVar = OptionVar
	BoolVar = BoolVar
	IntVar = IntVar
	RoleVar = RoleVar
	TextChanVar = TextChanVar
	DurationVar = DurationVar


class VerifyError(BaseException):
	def __init__(self, message=None):
		self.message=message