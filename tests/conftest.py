"""Shared test fixtures.

The suite runs against a real Postgres + Redis (the ``docker compose`` stack is
enough). It uses a dedicated ``marketplace_test`` database that is created and
migrated once per session, then truncated between tests.

Point it elsewhere with ``TEST_DATABASE_URL`` / ``TEST_REDIS_URL``.
"""
import os

_DEFAULT_DB = "postgresql://marketplace:marketplace_pass@localhost:5433/marketplace_test"
_DEFAULT_REDIS = "redis://localhost:6379/1"

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", _DEFAULT_DB)
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", _DEFAULT_REDIS)

import asyncio  # noqa: E402
import uuid  # noqa: E402
from urllib.parse import urlsplit, urlunsplit  # noqa: E402

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from src.auth.utils import create_access_token, hash_password  # noqa: E402
from src.config import settings  # noqa: E402
from src.database import close_db_connection, connect_to_db, get_pool  # noqa: E402
from src.main import app  # noqa: E402
from src.redis_client import close_redis_connection, connect_to_redis, get_redis  # noqa: E402

TABLES_TO_CLEAN = ["idempotency_keys", "order_items", "orders", "products", "users"]


async def _ensure_test_database() -> None:
    parts = urlsplit(settings.database_url)
    db_name = parts.path.lstrip("/")
    admin_dsn = urlunsplit(parts._replace(path="/postgres"))

    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def _run_migrations() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
async def _bootstrap():
    await _ensure_test_database()
    await asyncio.to_thread(_run_migrations)  # alembic env.py calls asyncio.run internally
    await connect_to_db()
    await connect_to_redis()
    await get_redis().flushdb()
    yield
    await close_db_connection()
    await close_redis_connection()


@pytest.fixture
async def db_pool():
    return get_pool()


@pytest.fixture(autouse=True)
async def _clean_state(_bootstrap):
    async with get_pool().acquire() as conn:
        await conn.execute(f"TRUNCATE {', '.join(TABLES_TO_CLEAN)} RESTART IDENTITY CASCADE")
    await get_redis().flushdb()
    yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_pool):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email",
            email,
            hash_password("password123"),
        )
    return {"id": row["id"], "email": row["email"], "token": create_access_token(row["id"])}


@pytest.fixture
def auth_headers(test_user):
    return {"Authorization": f"Bearer {test_user['token']}"}


@pytest.fixture
async def test_product(db_pool):
    async def _create(name="Test Product", price="19.99", stock=10):
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO products (name, price, stock_quantity)
                VALUES ($1, $2, $3)
                RETURNING id, name, price, stock_quantity
                """,
                name,
                price,
                stock,
            )
        return dict(row)

    return _create
