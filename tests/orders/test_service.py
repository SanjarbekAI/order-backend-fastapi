import pytest

from src.orders.exceptions import InsufficientStock, InvalidOrderState, OrderNotFound
from src.orders.schemas import OrderItemIn
from src.orders.service import OrderService


@pytest.fixture
def service():
    return OrderService()


async def test_create_order_reserves_stock(service, test_user, test_product):
    product = await test_product(stock=10)
    items = [OrderItemIn(product_id=product["id"], quantity=3)]

    order = await service.create_order(test_user["id"], items, "key-1")

    assert order["status"] == "pending"
    assert order["items"][0]["quantity"] == 3


async def test_create_order_insufficient_stock_raises(service, test_user, test_product):
    product = await test_product(stock=2)
    items = [OrderItemIn(product_id=product["id"], quantity=5)]

    with pytest.raises(InsufficientStock):
        await service.create_order(test_user["id"], items, "key-2")


async def test_get_order_not_found_raises(service, test_user):
    with pytest.raises(OrderNotFound):
        await service.get_order(999999, test_user["id"])


async def test_get_order_of_another_user_raises(service, db_pool, test_user, test_product):
    product = await test_product(stock=10)
    order = await service.create_order(test_user["id"], [OrderItemIn(product_id=product["id"], quantity=1)], "key-x")

    async with db_pool.acquire() as conn:
        other_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash) VALUES ('other@example.com', 'x') RETURNING id"
        )

    with pytest.raises(OrderNotFound):
        await service.get_order(order["id"], other_id)


async def test_cancel_order_restores_stock(service, db_pool, test_user, test_product):
    product = await test_product(stock=10)
    items = [OrderItemIn(product_id=product["id"], quantity=4)]
    order = await service.create_order(test_user["id"], items, "key-3")

    await service.cancel_order(order["id"], test_user["id"])

    from src.products.repository import ProductRepository

    async with db_pool.acquire() as conn:
        updated_product = await ProductRepository().get_by_id(conn, product["id"])
    assert updated_product["stock_quantity"] == 10


async def test_cancel_already_cancelled_order_raises(service, test_user, test_product):
    product = await test_product(stock=10)
    items = [OrderItemIn(product_id=product["id"], quantity=1)]
    order = await service.create_order(test_user["id"], items, "key-4")

    await service.cancel_order(order["id"], test_user["id"])

    with pytest.raises(InvalidOrderState):
        await service.cancel_order(order["id"], test_user["id"])


async def test_duplicate_idempotency_key_returns_same_order(service, test_user, test_product):
    product = await test_product(stock=10)
    items = [OrderItemIn(product_id=product["id"], quantity=2)]

    first = await service.create_order(test_user["id"], items, "dup-key")
    second = await service.create_order(test_user["id"], items, "dup-key")

    assert first["id"] == second["id"]
