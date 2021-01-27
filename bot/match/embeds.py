from discord import Embed, Colour
from core.client import dc


class Embeds:
	""" This class generates discord embeds for various match states """

	def __init__(self, match):
		self.m = match
		# self.icon_url = f"https://cdn.discordapp.com/avatars/{dc.user.id}/{dc.user.avatar}.png?size=64"
		self.icon_url = "https://cdn.discordapp.com/avatars/240843400457355264/a51a5bf3b34d94922fd60751ba1d60ab.png?size=64"

	def check_in(self, not_ready):
		embed = Embed(
			colour=Colour(0xf5d858),
			title=self.m.gt("__**{queue}** is now on the check-in stage!__").format(
				queue=self.m.queue.name.capitalize()
			)
		)
		embed.add_field(
			name=self.m.gt("Waiting on:"),
			value="\n".join((f" \u200b <@{p.id}>" for p in not_ready)),
			inline=False
		)
		embed.add_field(
			name="—",
			value=self.m.gt(
				"Please react with {ready_emoji} to **check-in** or {not_ready_emoji} to **abort**!").format(
				ready_emoji=self.m.check_in.READY_EMOJI, not_ready_emoji=self.m.check_in.NOT_READY_EMOJI
			) + "\n\u200b",
			inline=False
		)
		embed.set_footer(
			text="Match id: 157947",
			icon_url=self.icon_url)

		return embed

	def draft(self):
		embed = Embed(
			colour=Colour(0x8758f5),
			title=self.m.gt("__**{queue}** is now on the draft stage!__").format(
				queue=self.m.queue.name.capitalize()
			)
		)

		teams_names = [
			f"{t.emoji} \u200b **{t.name}**" +
			(f" \u200b `〈{sum((self.m.ratings[p.id] for p in t))}〉`" if self.m.ranked else "")
			for t in self.m.teams[:2]
		]
		team_players = [
			" \u200b ".join([
				(f"`{self.m.rank_str(p)}" if self.m.ranked else "`") + f"{p.nick or p.name}`"
				for p in t
			]) if len(t) else "empty"
			for t in self.m.teams[:2]
		]
		embed.add_field(name=teams_names[0], value=" \u200b ❲ \u200b " + team_players[0] + " \u200b ❳", inline=False)
		embed.add_field(name=teams_names[1], value=" \u200b ❲ \u200b " + team_players[1] + " \u200b ❳\n\u200b", inline=False)

		embed.add_field(
			name=self.m.gt("Unpicked:"),
			value="\n".join((
				" \u200b `{rank}{name}`".format(
					rank=self.m.rank_str(p) if self.m.ranked else "",
					name=p.nick or p.name
				)
			) for p in self.m.teams[2]),
			inline=False
		)

		if len(self.m.teams[0]) and len(self.m.teams[1]):
			msg = self.m.gt(f"Pick players with `{self.m.qc.cfg.prefix}pick @player` command.")
			pick_step = len(self.m.teams[0]) + len(self.m.teams[1]) - 2
			picker_team = self.m.teams[self.m.draft.pick_order[pick_step]] if pick_step < len(self.m.draft.pick_order)-1 else None
			if picker_team:
				msg += "\n" + self.m.gt("{member}'s turn to pick!").format(member=f"<@{picker_team[0].id}>")
		else:
			msg = self.m.gt("Type {cmd} to become a captain and start picking teams.").format(
				cmd=f"`{self.m.qc.cfg.prefix}capfor {'/'.join((team.name.lower() for team in self.m.teams))}`"
			)

		embed.add_field(name="—", value=msg + "\n\u200b", inline=False)
		embed.set_footer(text="Match id: 157947", icon_url=self.icon_url)

		return embed

	def final_message(self):
		embed = Embed(
			colour=Colour(0x27b75e),
			title=self.m.qc.gt("__**{queue}** is started!__").format(queue=self.m.queue.name.capitalize())
		)

		if len(self.m.teams[0]) == 1 and len(self.m.teams[1]) == 1:  # 1v1
			p1, p2 = self.m.teams[0][0], self.m.teams[1][0]
			players = " \u200b {player1}{rating1}\n \u200b {player2}{rating2}".format(
				rating1=f" \u200b `〈{self.m.ratings[p1.id]}〉`" if self.m.ranked else "",
				player1=f"<@{p1.id}>",
				rating2=f" \u200b `〈{self.m.ratings[p1.id]}〉`" if self.m.ranked else "",
				player2=f"<@{p2.id}>",
			)
			embed.add_field(name="Players", value=players, inline=False)
		else:  # team vs team
			teams_names = [
				f"{t.emoji} \u200b **{t.name}**" +
				(f" \u200b `〈{sum((self.m.ratings[p.id] for p in t))}〉`" if self.m.ranked else "")
				for t in self.m.teams[:2]
			]
			team_players = [
				" \u200b " +
				" \u200b ".join([
					(f"`{self.m.rank_str(p)}`" if self.m.ranked else "") + f"<@{p.id}>"
					for p in t
				])
				for t in self.m.teams[:2]
			]
			team_players[1] += "\n\u200b"  # Extra empty line
			embed.add_field(name=teams_names[0], value=team_players[0], inline=False)
			embed.add_field(name=teams_names[1], value=team_players[1], inline=False)

		if len(self.m.maps):
			embed.add_field(
				name=self.m.qc.gt("Map" if len(self.m.maps) == 1 else "Maps"),
				value="\n".join((f"**{i}**" for i in self.m.maps)),
				inline=True
			)
		if self.m.server:
			embed.add_field(name=self.qc.gt("Server"), value=f"`{self.server}`", inline=True)
		if self.m.start_msg:
			embed.add_field(name="—", value=self.m.start_msg + "\n\u200b", inline=False)
		embed.set_footer(text="Match id: 157947", icon_url=self.icon_url)

		return embed
