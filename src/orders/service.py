"""Order use-cases: placement (idempotent, stock-reserving), retrieval, cancel.

Transaction model
-----------------
``create_order`` and ``cancel_order`` each run as a single Postgres
transaction (``READ COMMITTED``). All correctness under concurrency comes from
the database:

* stock is decremented with a conditional ``UPDATE ... WHERE stock >= n`` — see
  ``ProductRepository.reserve_stock``;
* the idempotency record is inserted last; a losing concurrent duplicate hits
  the ``UNIQUE (user_id, key)`` constraint, the whole transaction rolls back
  (including the stock decrement), and we return the winner's stored response.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg

from src.config import settings
from src.database import get_pool
from src.idempotency.exceptions import DuplicateIdempotencyKey
from src.idempotency.service import IdempotencyService
from src.orders.constants import OrderStatus
from src.orders.exceptions import InsufficientStock, InvalidOrderState, OrderNotFound
from src.orders.repository import OrderRepository
from src.orders.schemas import OrderItemIn
from src.products.cache import ProductCache
from src.products.repository import ProductRepository
from src.redis_client import get_redis

_ORDERS_ENDPOINT = "POST /orders"


class OrderService:
    def __init__(self) -> None:
        self.orders = OrderRepository()
        self.products = ProductRepository()
        self.idempotency = IdempotencyService()
        self.product_cache = ProductCache(get_redis())

    async def create_order(
        self, user_id: int, items: list[OrderItemIn], idempotency_key: str
    ) -> dict:
        pool = get_pool()

        # A losing concurrent duplicate rolls its own transaction back; by the
        # time UniqueViolation surfaces the winner has committed, so a single
        # retry (whose in-transaction check now finds the stored response) is
        # always enough.
        for attempt in range(2):
            try:
                response_body, touched_product_ids = await self._place_order(
                    pool, user_id, items, idempotency_key
                )
            except DuplicateIdempotencyKey:
                if attempt == 0:
                    continue
                raise

            for product_id in touched_product_ids:
                await self.product_cache.invalidate(product_id)
            return response_body

        raise RuntimeError("unreachable")  # pragma: no cover

    async def _place_order(
        self,
        pool: asyncpg.Pool,
        user_id: int,
        items: list[OrderItemIn],
        idempotency_key: str,
    ) -> tuple[dict, list[int]]:
        async with pool.acquire() as conn:
            async with conn.transaction():
                stored = await self.idempotency.get_stored_response(conn, user_id, idempotency_key)
                if stored is not None:
                    return stored, []

                total_amount = 0
                reserved: list[tuple[int, int, object]] = []
                for item in items:
                    product = await self.products.get_by_id(conn, item.product_id)
                    if product is None or not await self.products.reserve_stock(
                        conn, item.product_id, item.quantity
                    ):
                        raise InsufficientStock(item.product_id)
                    total_amount += product["price"] * item.quantity
                    reserved.append((item.product_id, item.quantity, product["price"]))

                expires_at = datetime.now(UTC) + timedelta(
                    minutes=settings.order_reservation_minutes
                )
                order = await self.orders.create(conn, user_id, total_amount, expires_at)
                for product_id, quantity, price in reserved:
                    await self.orders.add_item(conn, order["id"], product_id, quantity, price)

                order_items = await self.orders.get_items(conn, order["id"])
                response_body = _serialize_order(order, order_items)

                await self.idempotency.store_response(
                    conn, user_id, idempotency_key, _ORDERS_ENDPOINT, response_body, 201
                )

        return response_body, [pid for pid, _, _ in reserved]

    async def get_order(self, order_id: int, user_id: int) -> dict:
        async with get_pool().acquire() as conn:
            order = await self.orders.get_by_id(conn, order_id)
            if order is None or order["user_id"] != user_id:
                raise OrderNotFound(order_id)
            items = await self.orders.get_items(conn, order_id)
        return _serialize_order(order, items)

    async def cancel_order(self, order_id: int, user_id: int) -> dict:
        async with get_pool().acquire() as conn:
            async with conn.transaction():
                order = await self.orders.get_by_id(conn, order_id)
                if order is None or order["user_id"] != user_id:
                    raise OrderNotFound(order_id)
                if order["status"] != OrderStatus.PENDING:
                    raise InvalidOrderState(order_id, order["status"])

                updated = await self.orders.update_status(
                    conn, order_id, OrderStatus.CANCELLED,
                    expected_current_status=OrderStatus.PENDING,
                )
                if not updated:
                    # Lost the race to the expiry sweeper or a parallel cancel.
                    raise InvalidOrderState(order_id, "already processed")

                items = await self.orders.get_items(conn, order_id)
                for item in items:
                    await self.products.restore_stock(conn, item["product_id"], item["quantity"])

        for item in items:
            await self.product_cache.invalidate(item["product_id"])

        order["status"] = OrderStatus.CANCELLED
        return _serialize_order(order, items)


def _serialize_order(order: dict, items: list[dict]) -> dict:
    """Build the JSON-native response shape.

    Also the exact payload persisted in ``idempotency_keys.response_body``, so a
    replayed request returns a byte-identical body.
    """
    return {
        "id": order["id"],
        "user_id": order["user_id"],
        "status": str(order["status"]),
        "total_amount": str(order["total_amount"]),
        "expires_at": order["expires_at"].isoformat(),
        "created_at": order["created_at"].isoformat(),
        "items": [
            {
                "product_id": i["product_id"],
                "quantity": i["quantity"],
                "price_at_purchase": str(i["price_at_purchase"]),
            }
            for i in items
        ],
    }
