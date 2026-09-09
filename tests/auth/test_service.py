import pytest

from src.auth.exceptions import InvalidCredentials, UserAlreadyExists
from src.auth.service import AuthService

service = AuthService()


async def test_register_creates_user():
    user = await service.register("new@example.com", "password123")
    assert user["email"] == "new@example.com"
    assert "id" in user


async def test_register_duplicate_email_raises():
    await service.register("dup@example.com", "password123")
    with pytest.raises(UserAlreadyExists):
        await service.register("dup@example.com", "password123")


async def test_login_success_returns_token():
    await service.register("login@example.com", "password123")
    token = await service.login("login@example.com", "password123")
    assert isinstance(token, str)
    assert len(token) > 0


async def test_login_wrong_password_raises():
    await service.register("wrongpass@example.com", "password123")
    with pytest.raises(InvalidCredentials):
        await service.login("wrongpass@example.com", "wrongpassword")


async def test_login_nonexistent_user_raises():
    with pytest.raises(InvalidCredentials):
        await service.login("doesnotexist@example.com", "password123")