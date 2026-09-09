async def _place(client, headers, product_id, quantity, key):
    return await client.post(
        "/orders",
        headers={**headers, "Idempotency-Key": key},
        json={"items": [{"product_id": product_id, "quantity": quantity}]},
    )


async def test_create_order_endpoint(client, auth_headers, test_product):
    product = await test_product(stock=10)
    response = await _place(client, auth_headers, product["id"], 2, "router-key-1")
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


async def test_create_order_without_idempotency_key_returns_422(client, auth_headers, test_product):
    product = await test_product(stock=10)
    response = await client.post(
        "/orders",
        headers=auth_headers,
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )
    assert response.status_code == 422


async def test_create_order_without_token_returns_401(client, test_product):
    product = await test_product(stock=10)
    response = await client.post(
        "/orders",
        headers={"Idempotency-Key": "no-token"},
        json={"items": [{"product_id": product["id"], "quantity": 1}]},
    )
    assert response.status_code == 401


async def test_create_order_insufficient_stock_returns_409(client, auth_headers, test_product):
    product = await test_product(stock=1)
    response = await _place(client, auth_headers, product["id"], 5, "router-key-2")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


async def test_get_order_endpoint(client, auth_headers, test_product):
    product = await test_product(stock=10)
    order_id = (await _place(client, auth_headers, product["id"], 1, "router-key-3")).json()["id"]

    response = await client.get(f"/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == order_id


async def test_get_order_not_found_returns_404(client, auth_headers):
    response = await client.get("/orders/999999", headers=auth_headers)
    assert response.status_code == 404


async def test_cancel_order_endpoint(client, auth_headers, test_product):
    product = await test_product(stock=10)
    order_id = (await _place(client, auth_headers, product["id"], 2, "router-key-4")).json()["id"]

    response = await client.post(f"/orders/{order_id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_cancel_nonexistent_order_returns_404(client, auth_headers):
    response = await client.post("/orders/999999/cancel", headers=auth_headers)
    assert response.status_code == 404
