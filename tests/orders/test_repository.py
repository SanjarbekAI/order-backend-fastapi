from datetime import UTC, datetime, timedelta

from src.orders.constants import ORDER_STATUS_CANCELLED, ORDER_STATUS_PENDING
from src.orders.repository import OrderRepository

repo = OrderRepository()


async def test_create_order(db_pool, test_user):
    async with db_pool.acquire() as conn:
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        order = await repo.create(conn, test_user["id"], "100.00", expires_at)
    assert order["status"] == ORDER_STATUS_PENDING
    assert order["user_id"] == test_user["id"]


async def test_add_item_and_get_items(db_pool, test_user, test_product):
    product = await test_product(stock=10)
    async with db_pool.acquire() as conn:
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        order = await repo.create(conn, test_user["id"], "20.00", expires_at)
        await repo.add_item(conn, order["id"], product["id"], 2, product["price"])
        items = await repo.get_items(conn, order["id"])
    assert len(items) == 1
    assert items[0]["quantity"] == 2


async def test_update_status_with_expected_current_status(db_pool, test_user):
    async with db_pool.acquire() as conn:
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        order = await repo.create(conn, test_user["id"], "10.00", expires_at)
        updated = await repo.update_status(
            conn, order["id"], ORDER_STATUS_CANCELLED, expected_current_status=ORDER_STATUS_PENDING
        )
    assert updated is True


async def test_update_status_fails_if_status_mismatch(db_pool, test_user):
    async with db_pool.acquire() as conn:
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        order = await repo.create(conn, test_user["id"], "10.00", expires_at)
        # cancel it first
        await repo.update_status(conn, order["id"], ORDER_STATUS_CANCELLED, expected_current_status=ORDER_STATUS_PENDING)
        # try to cancel again — should fail since it's no longer 'pending'
        updated_again = await repo.update_status(
            conn, order["id"], ORDER_STATUS_CANCELLED, expected_current_status=ORDER_STATUS_PENDING
        )
    assert updated_again is False


async def test_claim_expired_pending(db_pool, test_user):
    async with db_pool.acquire() as conn:
        past = datetime.now(UTC) - timedelta(minutes=1)
        created = await repo.create(conn, test_user["id"], "10.00", past)
        expired = await repo.claim_expired_pending(conn)
    assert expired == [created["id"]]