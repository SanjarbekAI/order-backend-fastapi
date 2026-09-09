async def test_create_product_endpoint(client, auth_headers):
    response = await client.post(
        "/products",
        headers=auth_headers,
        json={"name": "Router Widget", "price": 12.50, "stock_quantity": 30},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Router Widget"
    assert body["stock_quantity"] == 30


async def test_create_product_requires_auth(client):
    response = await client.post(
        "/products", json={"name": "X", "price": 1, "stock_quantity": 1}
    )
    assert response.status_code == 401


async def test_get_product_endpoint(client, auth_headers):
    create_resp = await client.post(
        "/products",
        headers=auth_headers,
        json={"name": "Fetchable", "price": 1.00, "stock_quantity": 5},
    )
    product_id = create_resp.json()["id"]

    response = await client.get(f"/products/{product_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Fetchable"


async def test_get_product_not_found_returns_404(client):
    response = await client.get("/products/999999")
    assert response.status_code == 404


async def test_create_product_invalid_price_returns_422(client, auth_headers):
    response = await client.post(
        "/products",
        headers=auth_headers,
        json={"name": "Bad", "price": -5, "stock_quantity": 10},
    )
    assert response.status_code == 422
