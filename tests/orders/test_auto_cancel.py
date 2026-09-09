from datetime import UTC, datetime, timedelta

from src.background_jobs.tasks import cancel_expired_orders
from src.orders.repository import OrderRepository
from src.products.repository import ProductRepository

order_repo = OrderRepository()
product_repo = ProductRepository()


async def test_auto_cancel_expired_pending_order(db_pool, test_user, test_product):
    product = await test_product(stock=10)

    async with db_pool.acquire() as conn:
        past = datetime.now(UTC) - timedelta(minutes=1)
        order = await order_repo.create(conn, test_user["id"], "10.00", past)
        await order_repo.add_item(conn, order["id"], product["id"], 3, product["price"])
        await product_repo.reserve_stock(conn, product["id"], 3)

    ctx = {"db_pool": db_pool}
    result = await cancel_expired_orders(ctx)

    assert result["cancelled"] == 1

    async with db_pool.acquire() as conn:
        updated_order = await order_repo.get_by_id(conn, order["id"])
        updated_product = await product_repo.get_by_id(conn, product["id"])

    assert updated_order["status"] == "cancelled"
    assert updated_product["stock_quantity"] == 10  # restored


async def test_auto_cancel_does_not_touch_non_expired_orders(db_pool, test_user, test_product):
    await test_product(stock=10)

    async with db_pool.acquire() as conn:
        future = datetime.now(UTC) + timedelta(minutes=15)
        order = await order_repo.create(conn, test_user["id"], "10.00", future)

    ctx = {"db_pool": db_pool}
    result = await cancel_expired_orders(ctx)

    assert result["cancelled"] == 0

    async with db_pool.acquire() as conn:
        unchanged_order = await order_repo.get_by_id(conn, order["id"])
    assert unchanged_order["status"] == "pending"