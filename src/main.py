from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.auth.router import router as auth_router
from src.database import close_db_connection, connect_to_db, get_pool
from src.exceptions import register_exception_handlers
from src.orders.router import router as orders_router
from src.products.router import router as products_router
from src.redis_client import close_redis_connection, connect_to_redis, get_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_db()
    await connect_to_redis()
    yield
    await close_db_connection()
    await close_redis_connection()


app = FastAPI(title="Order & Inventory Reservation Service", version="1.0.0", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(orders_router)


@app.get("/health", tags=["ops"])
async def health_check() -> dict:
    async with get_pool().acquire() as conn:
        db_ok = await conn.fetchval("SELECT 1") == 1
    redis_ok = bool(await get_redis().ping())
    healthy = db_ok and redis_ok
    return {"status": "ok" if healthy else "degraded", "database": db_ok, "redis": redis_ok}
