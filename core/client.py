# -*- coding: utf-8 -*-
import discord
from asyncio import iscoroutinefunction
from core.console import log


class DiscordClient(discord.Client):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.was_ready = False
		self.events = dict(on_init=[], on_think=[], on_exit=[])
		self.commands = dict()

	def event(self, coro):
		"""This function replaces original decorator (that registers an event to listen to)
		allowing multiple functions to be registered on a single event.
		"""

		if not iscoroutinefunction(coro):
			raise TypeError('event registered must be a coroutine function')

		if coro.__name__ not in self.events.keys():
			self.events[coro.__name__] = [coro]

			async def run_event(*args, **kwargs):
				for task in self.events[coro.__name__]:
					await task(*args, **kwargs)

			setattr(self, coro.__name__, run_event)

		else:
			self.events[coro.__name__].append(coro)

	def command(self, *aliases):

		def wrapper(coro):
			if not iscoroutinefunction(coro):
				raise TypeError('command registered must be a coroutine function')

			for alias in aliases:
				if alias in self.commands.keys():
					raise KeyError('a command with this alias already exists')

				self.commands[alias] = coro
				log.debug('{} command alias registered from {}.'.format(alias, coro.__module__))

		return wrapper


dc = DiscordClient()
