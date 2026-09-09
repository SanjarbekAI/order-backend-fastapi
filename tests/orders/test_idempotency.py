from src.products.repository import ProductRepository


async def test_duplicate_idempotency_key_returns_same_order(client, auth_headers, test_product, db_pool):
    product = await test_product(stock=10)
    payload = {"items": [{"product_id": product["id"], "quantity": 3}]}
    headers = {**auth_headers, "Idempotency-Key": "idem-test-key"}

    first = await client.post("/orders", headers=headers, json=payload)
    second = await client.post("/orders", headers=headers, json=payload)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    async with db_pool.acquire() as conn:
        updated = await ProductRepository().get_by_id(conn, product["id"])
    assert updated["stock_quantity"] == 7  # decremented once, not twice


async def test_different_idempotency_keys_create_separate_orders(client, auth_headers, test_product):
    product = await test_product(stock=10)
    payload = {"items": [{"product_id": product["id"], "quantity": 1}]}

    resp1 = await client.post("/orders", headers={**auth_headers, "Idempotency-Key": "key-a"}, json=payload)
    resp2 = await client.post("/orders", headers={**auth_headers, "Idempotency-Key": "key-b"}, json=payload)

    assert resp1.json()["id"] != resp2.json()["id"]


async def test_same_key_different_users_are_isolated(client, auth_headers, test_product, db_pool):
    """A key is scoped to (user_id, key): another user reusing the value must
    get their own fresh order, not a peek at someone else's."""
    product = await test_product(stock=10)
    payload = {"items": [{"product_id": product["id"], "quantity": 1}]}

    async with db_pool.acquire() as conn:
        other_id = await conn.fetchval(
            "INSERT INTO users (email, password_hash) VALUES ('u2@example.com', 'x') RETURNING id"
        )
    from src.auth.utils import create_access_token

    other_headers = {"Authorization": f"Bearer {create_access_token(other_id)}"}

    r1 = await client.post("/orders", headers={**auth_headers, "Idempotency-Key": "shared"}, json=payload)
    r2 = await client.post("/orders", headers={**other_headers, "Idempotency-Key": "shared"}, json=payload)

    assert r1.json()["id"] != r2.json()["id"]
    assert r2.json()["user_id"] == other_id
