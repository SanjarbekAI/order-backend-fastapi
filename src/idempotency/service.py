import asyncpg

from src.idempotency.exceptions import DuplicateIdempotencyKey
from src.idempotency.repository import IdempotencyRepository


class IdempotencyService:
    def __init__(self) -> None:
        self.repo = IdempotencyRepository()

    async def get_stored_response(
        self, conn: asyncpg.Connection, user_id: int, key: str
    ) -> dict | None:
        record = await self.repo.get(conn, user_id, key)
        return record["response_body"] if record else None

    async def store_response(
        self,
        conn: asyncpg.Connection,
        user_id: int,
        key: str,
        endpoint: str,
        response_body: dict,
        status_code: int,
    ) -> None:
        try:
            await self.repo.save(conn, user_id, key, endpoint, response_body, status_code)
        except asyncpg.UniqueViolationError as exc:
            raise DuplicateIdempotencyKey(key) from exc
