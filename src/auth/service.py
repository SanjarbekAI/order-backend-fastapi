import asyncpg

from src.auth.exceptions import InvalidCredentials, UserAlreadyExists
from src.auth.repository import UserRepository
from src.auth.utils import create_access_token, hash_password, verify_password
from src.database import get_pool


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register(self, email: str, password: str) -> dict:
        password_hash = hash_password(password)
        async with get_pool().acquire() as conn:
            try:
                return await self.repo.create(conn, email.lower(), password_hash)
            except asyncpg.UniqueViolationError as exc:
                raise UserAlreadyExists(email) from exc

    async def login(self, email: str, password: str) -> str:
        async with get_pool().acquire() as conn:
            user = await self.repo.get_by_email(conn, email.lower())

        if user is None or not verify_password(password, user["password_hash"]):
            raise InvalidCredentials()

        return create_access_token(user["id"])
