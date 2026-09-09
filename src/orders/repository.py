import asyncpg

from src.orders.constants import OrderStatus

_ORDER_COLUMNS = "id, user_id, status, total_amount, expires_at, created_at, updated_at"


class OrderRepository:
    """Raw-SQL data access for ``orders`` and ``order_items``."""

    async def create(
        self, conn: asyncpg.Connection, user_id: int, total_amount, expires_at
    ) -> dict:
        row = await conn.fetchrow(
            f"""
            INSERT INTO orders (user_id, status, total_amount, expires_at)
            VALUES ($1, 'pending', $2, $3)
            RETURNING {_ORDER_COLUMNS}
            """,
            user_id,
            total_amount,
            expires_at,
        )
        return dict(row)

    async def add_item(
        self,
        conn: asyncpg.Connection,
        order_id: int,
        product_id: int,
        quantity: int,
        price_at_purchase,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase)
            VALUES ($1, $2, $3, $4)
            """,
            order_id,
            product_id,
            quantity,
            price_at_purchase,
        )

    async def get_by_id(self, conn: asyncpg.Connection, order_id: int) -> dict | None:
        row = await conn.fetchrow(
            f"SELECT {_ORDER_COLUMNS} FROM orders WHERE id = $1", order_id
        )
        return dict(row) if row else None

    async def get_items(self, conn: asyncpg.Connection, order_id: int) -> list[dict]:
        rows = await conn.fetch(
            """
            SELECT product_id, quantity, price_at_purchase
            FROM order_items
            WHERE order_id = $1
            ORDER BY id
            """,
            order_id,
        )
        return [dict(r) for r in rows]

    async def update_status(
        self,
        conn: asyncpg.Connection,
        order_id: int,
        new_status: OrderStatus,
        expected_current_status: OrderStatus | None = None,
    ) -> bool:
        """Conditional status transition.

        When ``expected_current_status`` is given the row is only updated if it
        is still in that state. This is the guard that makes a user-triggered
        cancel and the background expiry sweep safe to race: exactly one of them
        updates a row, the other sees ``False``.
        """
        if expected_current_status is not None:
            row = await conn.fetchrow(
                """
                UPDATE orders SET status = $1
                WHERE id = $2 AND status = $3
                RETURNING id
                """,
                new_status,
                order_id,
                expected_current_status,
            )
        else:
            row = await conn.fetchrow(
                "UPDATE orders SET status = $1 WHERE id = $2 RETURNING id",
                new_status,
                order_id,
            )
        return row is not None

    async def claim_expired_pending(
        self, conn: asyncpg.Connection, limit: int = 100
    ) -> list[int]:
        """Lock and return a batch of pending orders past their reservation
        window. ``FOR UPDATE SKIP LOCKED`` lets several workers run the sweep
        concurrently without stepping on each other. Backed by
        ``idx_orders_pending_expires_at``.
        """
        rows = await conn.fetch(
            """
            SELECT id FROM orders
            WHERE status = 'pending' AND expires_at < now()
            ORDER BY expires_at
            LIMIT $1
            FOR UPDATE SKIP LOCKED
            """,
            limit,
        )
        return [r["id"] for r in rows]
