# -*- coding: utf-8 -*-
import glicko2
import trueskill
import time

from core.database import db
from core.utils import find, get_nick


class BaseRating:

	table = "qc_players"

	def __init__(self, channel_id, init_rp=1500, init_deviation=300, scale=100, reduction_scale=100):
		self.channel_id = channel_id
		self.init_rp = init_rp
		self.init_deviation = init_deviation
		self.scale = scale/100
		self.reduction_scale = reduction_scale/100

	def _scale_changes(self, player, r_change, d_change):
		p = player.copy()
		r_change = (r_change * self.scale) * self.reduction_scale if r_change < 0 else r_change * self.scale
		p['rating'] = max(0, int(p['rating'] + r_change))
		p['deviation'] = max(0, int(p['deviation'] + d_change))
		return p

	async def get_players(self, user_ids):
		""" Return rating or initial rating for each member """
		data = await db.select(
			['user_id', 'rating', 'deviation', 'channel_id', 'wins', 'losses', 'draws'], self.table,
			where={'channel_id': self.channel_id}
		)
		results = []
		for user_id in user_ids:
			if d := find(lambda p: p['user_id'] == user_id, data):
				if d['rating'] is None:
					d['rating'] = self.init_rp
					d['deviation'] = self.init_deviation
			else:
				d = dict(
					channel_id=self.channel_id, user_id=user_id, rating=self.init_rp,
					deviation=self.init_deviation, wins=0, losses=0, draws=0
				)
			results.append(d)
		return results

	async def set_rating(self, member, rating, deviation=None):
		old = await db.select_one(
			('rating', 'deviation'), self.table,
			where=dict(channel_id=self.channel_id, user_id=member.id)
		)

		if not old:
			await db.insert(
				self.table,
				dict(
					channel_id=self.channel_id, nick=get_nick(member), user_id=member.id,
					rating=rating, deviation=deviation or self.init_deviation
				)
			)
			old = dict(rating=self.init_rp, deviation=self.init_deviation)
		else:
			old['rating'] = old['rating'] or self.init_rp
			old['deviation'] = old['deviation'] or self.init_deviation
			await db.update(
					self.table,
					dict(rating=rating, deviation=deviation or old['deviation']),
					keys=dict(channel_id=self.channel_id, user_id=member.id)
				)

		await db.insert(
			"qc_rating_history",
			dict(
				channel_id=self.channel_id, user_id=member.id, at=int(time.time()), rating_before=old['rating'],
				deviation_before=old['deviation'], rating_change=rating-old['rating'],
				deviation_change=deviation-old['deviation'] if deviation else 0,
				match_id=None, reason='manual seeding'
			)
		)

	async def hide_player(self, user_id, hide=True):
		await db.update(self.table, dict(is_hidden=hide), keys=dict(channel_id=self.channel_id, user_id=user_id))

	async def snap_ratings(self, ranks_table):
		ranks = [i['rating'] for i in ranks_table if i['rating'] != 0]
		lowest = min(ranks)
		data = await db.select(('*',), self.table, where=dict(channel_id=self.channel_id))
		history = []
		now = int(time.time())
		for p in (p for p in data if p['rating'] is not None):
			new_rating = max([i for i in ranks if i <= p['rating']] + [lowest])
			history.append(dict(
				user_id=p['user_id'],
				channel_id=self.channel_id,
				at=now,
				rating_before=p['rating'],
				rating_change=new_rating - p['rating'],
				deviation_before=p['deviation'],
				deviation_change=0,
				match_id=None,
				reason="ratings snap"
			))
			p['rating'] = new_rating
		await db.delete(self.table, where={'channel_id': self.channel_id})
		await db.insert_many(self.table, data)
		await db.insert_many('qc_rating_history', history)

	async def reset(self):
		data = await db.select(('user_id', 'rating', 'deviation'), self.table, where=dict(channel_id=self.channel_id))
		history = []
		now = int(time.time())

		for p in data:
			if p['rating'] is not None and (p['rating'] != self.init_rp or p['deviation'] != self.init_deviation):
				history.append(dict(
					user_id=p['user_id'],
					channel_id=self.channel_id,
					at=now,
					rating_before=p['rating'],
					rating_change=self.init_rp-p['rating'],
					deviation_before=p['deviation'],
					deviation_change=self.init_deviation-p['deviation'],
					match_id=None,
					reason="ratings reset"
				))

		await db.update(
			self.table, dict(rating=None, deviation=None), keys=dict(channel_id=self.channel_id)
		)
		if len(history):
			await db.insert_many('qc_rating_history', history)


class FlatRating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def rate(self, winners, losers, draw=False):
		if not draw:
			results = []
			for p in winners:
				new = self._scale_changes(p, 10, 0)
				results.append(new)

			for p in losers:
				new = new = self._scale_changes(p, -10, 0)
				results.append(new)
		else:
			results = [self._scale_changes(p, 0, 0) for p in (*winners, *losers)]

		return results


class Glicko2Rating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def rate(self, winners, losers, draw=False):
		score_w = 0.5 if draw else 1
		score_l = 0.5 if draw else 0
		print("Scores:")
		print(score_l, score_w)

		avg_w = [
			[int(sum((p['rating'] for p in winners)) / len(winners))],  # average rating
			[int(sum((p['deviation'] for p in winners)) / len(winners))],  # average deviation
			[score_l]
		]
		avg_l = [
			[int(sum((p['rating'] for p in losers)) / len(losers))],  # average rating
			[int(sum((p['deviation'] for p in losers)) / len(losers))],  # average deviation
			[score_w]
		]

		po = glicko2.Player()
		results = []
		for p in winners:
			po.setRating(p['rating'])
			po.setRd(p['deviation'])
			po.update_player(*avg_l)
			new = self._scale_changes(p, po.getRating() - p['rating'], po.getRd() - p['deviation'])
			results.append(new)

		for p in losers:
			po.setRating(p['rating'])
			po.setRd(p['deviation'])
			po.update_player(*avg_w)
			new = self._scale_changes(p, po.getRating() - p['rating'], po.getRd() - p['deviation'])
			results.append(new)

		return results


class TrueSkillRating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.ts = trueskill.TrueSkill(
			mu=self.init_rp, sigma=self.init_deviation,
			beta=int(self.init_deviation/2), tau=int(self.init_deviation/100)
		)

	def rate(self, winners, losers, draw=False):
		g1 = [self.ts.create_rating(mu=p['rating'], sigma=p['deviation']) for p in winners]
		g2 = [self.ts.create_rating(mu=p['rating'], sigma=p['deviation']) for p in losers]

		ranks = [0, 0] if draw else [0, 1]
		g1, g2 = (list(i) for i in self.ts.rate((g1, g2), ranks=ranks))

		results = []
		for p in winners:
			res = g1.pop(0)
			new = self._scale_changes(p, res.mu - p['rating'], res.sigma - p['deviation'])
			results.append(new)

		for p in losers:
			res = g2.pop(0)
			new = self._scale_changes(p, res.mu - p['rating'], res.sigma - p['deviation'])
			results.append(new)

		return results
