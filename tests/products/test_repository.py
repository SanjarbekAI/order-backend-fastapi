from src.products.repository import ProductRepository

repo = ProductRepository()


async def test_create_product(db_pool):
    async with db_pool.acquire() as conn:
        product = await repo.create(conn, "Widget", 9.99, 50)
    assert product["name"] == "Widget"
    assert product["stock_quantity"] == 50


async def test_get_by_id_returns_product(db_pool, test_product):
    created = await test_product(name="Gadget", stock=5)
    async with db_pool.acquire() as conn:
        found = await repo.get_by_id(conn, created["id"])
    assert found["name"] == "Gadget"


async def test_get_by_id_returns_none_for_missing(db_pool):
    async with db_pool.acquire() as conn:
        found = await repo.get_by_id(conn, 999999)
    assert found is None


async def test_reserve_stock_success(db_pool, test_product):
    product = await test_product(stock=10)
    async with db_pool.acquire() as conn:
        ok = await repo.reserve_stock(conn, product["id"], 3)
        updated = await repo.get_by_id(conn, product["id"])
    assert ok is True
    assert updated["stock_quantity"] == 7


async def test_reserve_stock_fails_when_insufficient(db_pool, test_product):
    product = await test_product(stock=2)
    async with db_pool.acquire() as conn:
        ok = await repo.reserve_stock(conn, product["id"], 5)
        updated = await repo.get_by_id(conn, product["id"])
    assert ok is False
    assert updated["stock_quantity"] == 2  # unchanged


async def test_restore_stock(db_pool, test_product):
    product = await test_product(stock=5)
    async with db_pool.acquire() as conn:
        await repo.restore_stock(conn, product["id"], 3)
        updated = await repo.get_by_id(conn, product["id"])
    assert updated["stock_quantity"] == 8