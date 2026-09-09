async def test_register_endpoint(client):
    response = await client.post(
        "/auth/register",
        json={"email": "router@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "router@example.com"


async def test_register_duplicate_returns_409(client):
    await client.post("/auth/register", json={"email": "dup2@example.com", "password": "password123"})
    response = await client.post("/auth/register", json={"email": "dup2@example.com", "password": "password123"})
    assert response.status_code == 409


async def test_login_endpoint(client):
    await client.post("/auth/register", json={"email": "login2@example.com", "password": "password123"})
    response = await client.post("/auth/login", json={"email": "login2@example.com", "password": "password123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_invalid_credentials_returns_401(client):
    response = await client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert response.status_code == 401


async def test_protected_endpoint_without_token_returns_401(client):
    response = await client.post(
        "/orders",
        headers={"Idempotency-Key": "test-key"},
        json={"items": [{"product_id": 1, "quantity": 1}]},
    )
    assert response.status_code == 401