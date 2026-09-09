"""Background tasks run by the arq worker."""
from __future__ import annotations

import logging

from src.orders.constants import OrderStatus
from src.orders.repository import OrderRepository
from src.products.cache import ProductCache
from src.products.repository import ProductRepository
from src.redis_client import get_redis

logger = logging.getLogger("background_jobs")

_orders = OrderRepository()
_products = ProductRepository()


async def cancel_expired_orders(ctx: dict) -> dict:
    """Cancel pending orders whose reservation window has elapsed and return
    the reserved stock.

    Runs every minute (see ``WorkerSettings.cron_jobs``). Each batch is one
    transaction: ``claim_expired_pending`` locks the rows with
    ``FOR UPDATE SKIP LOCKED`` so multiple workers can share the load, and the
    conditional status update means a user cancelling at the same moment can
    never cause a double stock refund.
    """
    pool = ctx["db_pool"]
    cache = ProductCache(get_redis())

    cancelled = 0
    touched_products: set[int] = set()

    async with pool.acquire() as conn:
        async with conn.transaction():
            order_ids = await _orders.claim_expired_pending(conn)
            for order_id in order_ids:
                updated = await _orders.update_status(
                    conn, order_id, OrderStatus.CANCELLED,
                    expected_current_status=OrderStatus.PENDING,
                )
                if not updated:
                    continue
                for item in await _orders.get_items(conn, order_id):
                    await _products.restore_stock(conn, item["product_id"], item["quantity"])
                    touched_products.add(item["product_id"])
                cancelled += 1

    for product_id in touched_products:
        await cache.invalidate(product_id)

    if cancelled:
        logger.info("expiry sweep cancelled %d order(s)", cancelled)
    return {"cancelled": cancelled}
