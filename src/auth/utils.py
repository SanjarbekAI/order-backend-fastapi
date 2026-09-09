"""Password hashing (bcrypt) and JWT encode/decode helpers.

``bcrypt`` is used directly rather than through passlib: one less dependency and
no version-shim warnings. bcrypt ignores bytes past position 72, so passwords
are hard-limited to 72 bytes at the schema layer.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from src.auth.exceptions import InvalidToken
from src.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidToken() from exc
