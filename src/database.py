"""asyncpg connection-pool lifecycle.

The pool is a module-level singleton created on app startup and reused by every
request. Repositories receive a ``Connection`` (never the pool) so the service
layer stays in control of transaction boundaries.
"""
from __future__ import annotations

import asyncpg

from src.config import settings

_pool: asyncpg.Pool | None = None


async def connect_to_db() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )
    return _pool


async def close_db_connection() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialised — connect_to_db() was not called")
    return _pool
