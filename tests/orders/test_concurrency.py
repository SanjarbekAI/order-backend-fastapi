import asyncio
import uuid


async def test_50_concurrent_orders_exactly_10_succeed(client, auth_headers, test_product):
    """
    Core requirement: with stock=10, 50 parallel requests for 1 unit each
    should result in exactly 10 successful (201) orders and 40 failed (409).
    """
    product = await test_product(stock=10)

    async def place_order():
        return await client.post(
            "/orders",
            headers={**auth_headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )

    responses = await asyncio.gather(*[place_order() for _ in range(50)])

    status_codes = [r.status_code for r in responses]
    successes = status_codes.count(201)
    failures = status_codes.count(409)

    assert successes == 10, f"Expected exactly 10 successes, got {successes}"
    assert failures == 40, f"Expected exactly 40 failures, got {failures}"
    assert successes + failures == 50


async def test_concurrent_orders_never_oversell(client, auth_headers, test_product, db_pool):
    """
    Stronger correctness check: after concurrent load, remaining stock
    must never go negative and must exactly match reservations made.
    """
    product = await test_product(stock=10)

    async def place_order():
        return await client.post(
            "/orders",
            headers={**auth_headers, "Idempotency-Key": str(uuid.uuid4())},
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )

    responses = await asyncio.gather(*[place_order() for _ in range(50)])
    successes = sum(1 for r in responses if r.status_code == 201)

    from src.products.repository import ProductRepository
    async with db_pool.acquire() as conn:
        final_product = await ProductRepository().get_by_id(conn, product["id"])

    assert final_product["stock_quantity"] == 10 - successes
    assert final_product["stock_quantity"] >= 0


async def test_concurrent_same_idempotency_key_reserves_stock_once(client, auth_headers, test_product, db_pool):
    """10 parallel requests sharing one Idempotency-Key: all return the same
    order and stock is decremented exactly once."""
    product = await test_product(stock=10)
    headers = {**auth_headers, "Idempotency-Key": "race-key"}
    payload = {"items": [{"product_id": product["id"], "quantity": 2}]}

    responses = await asyncio.gather(
        *[client.post("/orders", headers=headers, json=payload) for _ in range(10)]
    )

    assert all(r.status_code == 201 for r in responses)
    assert len({r.json()["id"] for r in responses}) == 1

    from src.products.repository import ProductRepository
    async with db_pool.acquire() as conn:
        final = await ProductRepository().get_by_id(conn, product["id"])
    assert final["stock_quantity"] == 8