"""Redis client lifecycle (async, module-level singleton)."""
from __future__ import annotations

import redis.asyncio as redis

from src.config import settings

_redis: redis.Redis | None = None


async def connect_to_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis_connection() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis client is not initialised — connect_to_redis() was not called")
    return _redis
