import json

import asyncpg


class IdempotencyRepository:
    """Raw-SQL access to ``idempotency_keys``.

    Uniqueness is on ``(user_id, key)`` so one client's key can never collide
    with another's, and a client may safely reuse a key value across accounts.
    """

    async def get(self, conn: asyncpg.Connection, user_id: int, key: str) -> dict | None:
        row = await conn.fetchrow(
            """
            SELECT key, user_id, endpoint, response_body, status_code, created_at
            FROM idempotency_keys
            WHERE user_id = $1 AND key = $2
            """,
            user_id,
            key,
        )
        if row is None:
            return None
        data = dict(row)
        data["response_body"] = json.loads(data["response_body"])
        return data

    async def save(
        self,
        conn: asyncpg.Connection,
        user_id: int,
        key: str,
        endpoint: str,
        response_body: dict,
        status_code: int,
    ) -> None:
        """INSERT that leans on the UNIQUE(user_id, key) constraint to detect a
        concurrent duplicate — raising ``asyncpg.UniqueViolationError``."""
        await conn.execute(
            """
            INSERT INTO idempotency_keys (user_id, key, endpoint, response_body, status_code)
            VALUES ($1, $2, $3, $4::jsonb, $5)
            """,
            user_id,
            key,
            endpoint,
            json.dumps(response_body),
            status_code,
        )
