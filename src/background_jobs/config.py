"""arq worker settings: `arq src.background_jobs.config.WorkerSettings`."""
from __future__ import annotations

import asyncpg
from arq.connections import RedisSettings
from arq.cron import cron

from src.background_jobs.tasks import cancel_expired_orders
from src.config import settings
from src.redis_client import close_redis_connection, connect_to_redis


async def startup(ctx: dict) -> None:
    ctx["db_pool"] = await asyncpg.create_pool(
        dsn=settings.database_url, min_size=1, max_size=5
    )
    await connect_to_redis()


async def shutdown(ctx: dict) -> None:
    await ctx["db_pool"].close()
    await close_redis_connection()


class WorkerSettings:
    functions = [cancel_expired_orders]
    cron_jobs = [cron(cancel_expired_orders, minute=set(range(60)), run_at_startup=True)]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
