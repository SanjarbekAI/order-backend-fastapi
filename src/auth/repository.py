import asyncpg


class UserRepository:
    """Raw-SQL data access for the ``users`` table."""

    async def create(self, conn: asyncpg.Connection, email: str, password_hash: str) -> dict:
        row = await conn.fetchrow(
            """
            INSERT INTO users (email, password_hash)
            VALUES ($1, $2)
            RETURNING id, email, created_at
            """,
            email,
            password_hash,
        )
        return dict(row)

    async def get_by_email(self, conn: asyncpg.Connection, email: str) -> dict | None:
        row = await conn.fetchrow(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = $1",
            email,
        )
        return dict(row) if row else None

    async def get_by_id(self, conn: asyncpg.Connection, user_id: int) -> dict | None:
        row = await conn.fetchrow(
            "SELECT id, email, created_at FROM users WHERE id = $1",
            user_id,
        )
        return dict(row) if row else None
