"""Redis cache for single-product reads.

Strategy: **cache-aside** with a short TTL and explicit invalidation.

* Reads (`GET /products/{id}`) populate the cache on a miss.
* Any write that changes stock (order reservation, cancellation, the expiry
  sweeper) deletes the key. Deleting rather than rewriting keeps the cache from
  being repopulated with a value from a transaction that later rolls back.
* The TTL (default 60s) is a safety net that bounds staleness if an
  invalidation is ever missed.

Prices/stock in the payload are stored as strings so JSON round-trips keep
``Decimal`` precision.
"""
from __future__ import annotations

import json
from decimal import Decimal

from redis.asyncio import Redis

from src.config import settings

_KEY_PREFIX = "product:"


def _key(product_id: int) -> str:
    return f"{_KEY_PREFIX}{product_id}"


def _serialize(product: dict) -> str:
    data = dict(product)
    data["price"] = str(data["price"])
    data["created_at"] = data["created_at"].isoformat()
    data["updated_at"] = data["updated_at"].isoformat()
    return json.dumps(data)


def _deserialize(raw: str) -> dict:
    data = json.loads(raw)
    data["price"] = Decimal(data["price"])
    return data


class ProductCache:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.ttl = settings.product_cache_ttl_seconds

    async def get(self, product_id: int) -> dict | None:
        raw = await self.redis.get(_key(product_id))
        return _deserialize(raw) if raw else None

    async def set(self, product_id: int, product: dict) -> None:
        await self.redis.set(_key(product_id), _serialize(product), ex=self.ttl)

    async def invalidate(self, product_id: int) -> None:
        await self.redis.delete(_key(product_id))
