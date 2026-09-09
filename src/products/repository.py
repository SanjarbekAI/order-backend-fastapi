import asyncpg


class ProductRepository:
    """Raw-SQL data access for the ``products`` table."""

    async def create(
        self, conn: asyncpg.Connection, name: str, price, stock_quantity: int
    ) -> dict:
        row = await conn.fetchrow(
            """
            INSERT INTO products (name, price, stock_quantity)
            VALUES ($1, $2, $3)
            RETURNING id, name, price, stock_quantity, created_at, updated_at
            """,
            name,
            price,
            stock_quantity,
        )
        return dict(row)

    async def get_by_id(self, conn: asyncpg.Connection, product_id: int) -> dict | None:
        row = await conn.fetchrow(
            """
            SELECT id, name, price, stock_quantity, created_at, updated_at
            FROM products
            WHERE id = $1
            """,
            product_id,
        )
        return dict(row) if row else None

    async def reserve_stock(
        self, conn: asyncpg.Connection, product_id: int, quantity: int
    ) -> bool:
        """Atomically decrement stock, but only if enough is on hand.

        Correctness under concurrency comes entirely from this one statement:
        the ``UPDATE`` takes a row lock, and any waiter re-evaluates
        ``stock_quantity >= $1`` against the just-committed value. With
        ``stock = 10`` and 50 concurrent callers, exactly 10 rows are updated;
        the rest match zero rows and get ``False``.
        """
        row = await conn.fetchrow(
            """
            UPDATE products
            SET stock_quantity = stock_quantity - $1
            WHERE id = $2 AND stock_quantity >= $1
            RETURNING stock_quantity
            """,
            quantity,
            product_id,
        )
        return row is not None

    async def restore_stock(
        self, conn: asyncpg.Connection, product_id: int, quantity: int
    ) -> None:
        await conn.execute(
            "UPDATE products SET stock_quantity = stock_quantity + $1 WHERE id = $2",
            quantity,
            product_id,
        )
