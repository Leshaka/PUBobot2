# -*- coding: utf-8 -*-
import random
import re
from prettytable import PrettyTable, MARKDOWN
from nextcord import Embed
from nextcord.utils import get, find, escape_markdown
from datetime import timedelta


class EmojiFormatter(object):
	""" Converts emoji name to an emoji string """

	def __init__(self, guild):
		self.guild = guild
		super().__init__()

	def __format__(self, string):
		try:
			return str(next(i for i in self.guild.emojis if i.name == string))
		except StopIteration:
			return ''


def random_string(length):
	letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
	return ''.join(random.choice(letters) for i in range(length))


def hl_user(user_id):
	return '<@' + str(user_id) + '>'


def join_and(names):
	""" Generates 'item1, item2, item3 & item4' string from a list """
	return ', '.join(names[:-1]) + f' & {names[-1]}' if len(names) > 1 else names[0]


def hl_role(role_id):
	return '<&' + str(role_id) + '>'


def error_embed(description, title='Error'):
	if title:
		return Embed(title=title, description=description, color=0xca0000)
	else:
		return Embed(description=description, color=0xca0000)


def ok_embed(description, title='Success'):
	if title:
		return Embed(title=title, description=description, color=0x32cd32)
	else:
		return Embed(description=description, color=0x32cd32)


def format_channel(string, guild):
	channel = get(guild.text_channels, name=string)
	return '<#{}>'.format(channel.id) if channel else None


def format_role(string, guild):
	role = get(guild.roles, name=string)
	return '<@&{}>'.format(role.id) if role else None


def format_emoji(string, guild):
	emoji = get(guild.emojis, name=string)
	return '<:{}:{}>'.format(emoji.name, emoji.id) if emoji else None


def format_message(_string, _guild, **kwargs):
	_string = re.sub('#([^ ,.!?]+)', lambda i: format_channel(i.group(1), _guild) or i.group(0), _string)
	_string = re.sub('@([^ ,.!?]+)', lambda i: format_role(i.group(1), _guild) or i.group(0), _string)
	_string = re.sub(':([^ ,.!?]+):', lambda i: format_emoji(i.group(1), _guild) or i.group(0), _string)
	return _string.format(**kwargs)


def escape(string):
	""" Escape discord text formatting characters """
	return re.sub('([`*_])', lambda i: '\\'+i.group(), string)


async def reply(msg, string):
	await msg.channel.send('<@{}>, {}'.format(msg.author.id, string))


def parse_duration(string):
	if string == 'inf':
		return 0

	if re.match(r"^\d\d:\d\d:\d\d$", string):
		x = sum(x * int(t) for x, t in zip([3600, 60, 1], string.split(":")))
		return timedelta(seconds=x)

	elif re.match(r"^(\d+\w ?)+$", string):
		duration = 0
		for part in re.findall(r"\d+\w", string):
			val = float(part[:-1])
			if part[-1] == 's':
				duration += val
			elif part[-1] == 'm':
				duration += val * 60
			elif part[-1] == 'h':
				duration += val * 60 * 60
			elif part[-1] == 'd':
				duration += val * 60 * 60 * 24
			elif part[-1] == 'W':
				duration += val * 60 * 60 * 24 * 7
			elif part[-1] == 'M':
				duration += val * 60 * 60 * 24 * 30
			elif part[-1] == 'Y':
				duration += val * 365 * 24 * 60
			else:
				raise ValueError()
		return timedelta(seconds=int(duration))
	else:
		raise ValueError()


def iter_to_dict(it, key):
	""" Converts an iterable of dictionaries to a dict """
	return {i[key]: i for i in it}


def seconds_to_str(seconds):
	return str(timedelta(seconds=seconds))


def escape_cb(string):
	""" Removes bad characters for string inside a dc codeblock """
	return re.sub(r"([`<>\*_\\\[\]\~])|((?=\s)[^ ])", "", string)


def get_nick(user):
	""" Remove rating tag and text formatting characters """
	string = user.nick or user.name
	if x := re.match(r"^\[\d+\] (.+)", string):
		string = x.group(1)
	return escape_cb(string)


def discord_table(header, rows):
	t = PrettyTable()
	t.set_style(MARKDOWN)
	t.header = False
	t.add_row(header)
	t.add_rows(rows)
	content = t.get_string().split("\n")
	text = "```markdown\n" + content[0].strip("|")
	text += "\n" + "-" * len(content[0]) + "\n"
	text += "\n".join(line.strip("|") for line in content[1:]) + "\n```"
	return text


def split_big_text(string: str, limit: int = 2000, delimiter: str = None, prefix: str = "", suffix: str = ""):
	""" Yields pieces with limited length and prefix and suffix attached. Split by delimiter if possible. """
	_limit = limit-len(prefix+suffix)
	while len(string) > _limit:
		if delimiter and (pos := string[:_limit].rfind(delimiter)) != -1:
			yield prefix + string[:pos+len(delimiter)] + suffix
			string = string[pos+len(delimiter):]
		else:
			yield prefix + string[:_limit] + suffix
			string = string[_limit:]
	if len(string):
		yield prefix + string + suffix


class SafeTemplateDict(dict):
	""" returns {key} for missing keys, useful for string.format_map() """
	def __missing__(self, key):
		return '{'+key+'}'
