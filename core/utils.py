# -*- coding: utf-8 -*-
import random
import re
from discord import Embed
from discord.utils import get, find, escape_markdown
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
	return Embed(title=title, description=description, color=0xca0000)


def ok_embed(description, title='Success'):
	return Embed(title=title, description=description, color=0x32cd32)


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

	duration = float(string[:-1])
	if string[-1] == 'm':
		duration = duration * 60
	elif string[-1] == 'h':
		duration = duration * 60 * 60
	elif string[-1] == 'd':
		duration = duration * 60 * 60 * 24
	elif string[-1] == 'W':
		duration = duration * 60 * 60 * 24 * 7
	elif string[-1] == 'M':
		duration = duration * 60 * 60 * 24 * 30
	elif string[-1] == 'Y':
		duration = duration * 60 * 60 * 24 * 30
	else:
		raise ValueError()
	return int(duration)


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
