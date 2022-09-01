__all__ = [
	'create_pickup', 'delete_queue', 'show_queues', 'set_qc', 'set_queue', 'cfg_qc', 'cfg_queue',
	'set_qc_cfg', 'set_queue_cfg'
]

import json
from core.utils import find, get
import bot


async def create_pickup(ctx, name: str, size: int = 8):
	""" Create new PickupQueue """
	ctx.check_perms(ctx.Perms.ADMIN)
	try:
		pq = await ctx.qc.new_queue(ctx, name, size, bot.PickupQueue)
	except ValueError as e:
		raise bot.Exc.ValueError(str(e))
	else:
		await ctx.success(f"[**{pq.name}** ({pq.status})]")


async def delete_queue(ctx, queue: str):
	""" Delete a queue """
	ctx.check_perms(ctx.Perms.ADMIN)
	if (q := get(ctx.qc.queues, name=queue)) is None:
		raise bot.Exc.NotFoundError(f"Queue '{queue}' not found on the channel..")
	await q.cfg.delete()
	ctx.qc.queues.remove(q)
	await show_queues(ctx)


async def show_queues(ctx):
	""" List all queues on the channel """
	if len(ctx.qc.queues):
		await ctx.reply("> [" + " | ".join(
			[f"**{q.name}** ({q.status})" for q in ctx.qc.queues]
		) + "]")
	else:
		await ctx.reply("> [ **no queues configured** ]")


async def set_qc(ctx, variable: str, value: str):
	""" Configure a QueueChannel variable """
	ctx.check_perms(ctx.Perms.ADMIN)

	if variable not in ctx.qc.cfg_factory.variables.keys():
		raise bot.Exc.SyntaxError(f"No such variable '{variable}'.")
	try:
		await ctx.qc.cfg.update({variable: value})
	except Exception as e:
		raise bot.Exc.ValueError(str(e))
	else:
		await ctx.success(f"Variable __{variable}__ configured.")


async def set_queue(ctx, queue: str, variable: str, value: str):
	""" Configure a Queue variable """
	ctx.check_perms(ctx.Perms.ADMIN)

	if (q := find(lambda i: i.name.lower() == queue.lower(), ctx.qc.queues)) is None:
		raise bot.Exc.SyntaxError(f"Queue '{queue}' not found on the channel.")
	if variable not in q.cfg_factory.variables.keys():
		raise bot.Exc.SyntaxError(f"No such variable '{variable}'.")

	try:
		await q.cfg.update({variable: value})
	except Exception as e:
		raise bot.Exc.ValueError(str(e))
	else:
		await ctx.success(f"**{q.name}** variable __{variable}__ configured.")


async def cfg_qc(ctx):
	""" List QueueChannel configuration """
	await ctx.reply_dm(f"```json\n{json.dumps(ctx.qc.cfg.readable(), ensure_ascii=False, indent=2)}```")


async def cfg_queue(ctx, queue: str):
	""" List a queue configuration """
	if (q := find(lambda i: i.name.lower() == queue.lower(), ctx.qc.queues)) is None:
		raise bot.Exc.SyntaxError(f"Queue '{queue}' not found on the channel.")
	await ctx.reply_dm(f"```json\n{json.dumps(q.cfg.readable(), ensure_ascii=False, indent=2)}```")


async def set_qc_cfg(ctx, cfg):
	""" Update QueueChannel configuration via JSON string """
	ctx.check_perms(ctx.Perms.ADMIN)
	try:
		await ctx.qc.cfg.update(json.loads(cfg))
	except Exception as e:
		raise bot.Exc.ValueError(str(e))
	else:
		await ctx.success(f"Channel configuration updated.")


async def set_queue_cfg(ctx, queue: str, cfg: str):
	""" Update queue configuration via JSON string """
	ctx.check_perms(ctx.Perms.ADMIN)
	if (q := find(lambda i: i.name.lower() == queue.lower(), ctx.qc.queues)) is None:
		raise bot.Exc.SyntaxError(f"Queue '{queue}' not found on the channel.")

	try:
		await q.cfg.update(json.loads(cfg))
	except Exception as e:
		raise bot.Exc.ValueError(str(e))
	else:
		await ctx.success(f"__{q.name}__ queue configuration updated.")
