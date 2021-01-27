# -*- coding: utf-8 -*-
import glicko2
import trueskill

from core.database import db
from core.utils import find

db.ensure_table(dict(
	tname="qc_ratings",
	columns=[
		dict(cname="channel_id", ctype=db.types.int),
		dict(cname="user_id", ctype=db.types.int),
		dict(cname="rating", ctype=db.types.int),
		dict(cname="deviation", ctype=db.types.int),
	],
	primary_keys=["channel_id", "user_id"]
))


class BaseRating:

	table = "qc_ratings"

	def __init__(self, channel_id, init_rp=1500, init_deviation=300, scale=32):
		self.channel_id = channel_id
		self.init_rp = init_rp
		self.init_deviation = init_deviation
		self.scale = scale

	async def get_ratings(self, user_ids=None, limit=None):
		data = await db.select(
			['user_id', 'rating', 'deviation', 'channel_id'], self.table,
			where={'channel_id': self.channel_id}, order_by="rating", limit=limit
		)
		if user_ids:
			return [
				find(lambda p: p['user_id'] == user_id, data) or
				dict(channel_id=self.channel_id, user_id=user_id, rating=self.init_rp, deviation=self.init_deviation)
				for user_id in user_ids
			]
		else:
			return data

	async def get_rating(self, user_id):
		data = await db.select_one(
			["rating", "deviation"], self.table,
			where={"channel_id": self.channel_id, "user_id": user_id}
		)
		return data or dict(rating=self.init_rp, deviation=self.init_deviation)

	async def set_ratings(self, results):
		await db.insert_many(self.table, results, on_dublicate="replace")


class FlatRating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.scale = int(self.scale/2)

	def rate(self, winners, losers, draw=False):
		if not draw:
			results = []
			for p in winners:
				new = p.copy()
				new['rating'] += self.scale
				results.append(new)

			for p in losers.keys():
				new = p.copy()
				new['rating'] = min((new['rating']-self.scale, 0))
				results.append(new)
		else:
			results = [p.copy() for p in (*winners, *losers)]

		return results


class Glicko2Rating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.scale = round(self.scale/32, 2)

	def rate(self, winners, losers, draw=False):
		score_w = 0.5 if draw else 1
		score_l = 0.5 if draw else 0

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
			new = p.copy()
			new.update({'rating': int(po.getRating()), 'deviation': int(po.getRd())})
			results.append(new)

		for p in losers:
			po.setRating(p['rating'])
			po.setRd(p['deviation'])
			po.update_player(*avg_w)
			new = p.copy()
			new.update({'rating': int(po.getRating()), 'deviation': int(po.getRd())})
			results.append(new)

		return results


class TrueSkillRating(BaseRating):

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.scale = (self.init_rp/6)/32*self.scale
		self.ts = trueskill.TrueSkill(
			mu=self.init_rp, sigma=self.init_deviation,
			beta=self.scale, tau=self.init_deviation/100
		)

	def rate(self, winners, losers, draw=False):
		g1 = [self.ts.create_rating(mu=p['rating'], sigma=p['deviation']) for p in winners.keys()]
		g2 = [self.ts.create_rating(mu=p['rating'], sigma=p['deviation']) for p in losers.keys()]

		ranks = [0, 0] if draw else [0, 1]
		g1, g2 = self.ts.rate((g1, g2), ranks=ranks)

		results = []
		for p in winners:
			res = g1.pop(0)
			new = p.copy()
			new.update({'rating': int(int(res.mu)), 'deviation': int(res.sigma)})
			results.append(new)

		for p in losers:
			res = g2.pop(0)
			new = p.copy()
			new.update({'rating': int(int(res.mu)), 'deviation': int(res.sigma)})
			results.append(new)

		return results
