"""
Core security utilities — JWT, password hashing, token management.
All functions are pure (no DB I/O) so they remain sync-friendly inside async routes.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────
ALGORITHM = "HS256"

TokenData = dict[str, Any]


def _create_token(data: TokenData, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    payload["iat"] = datetime.now(timezone.utc)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int, email: str, role: str) -> str:
    return _create_token(
        {"sub": str(user_id), "email": email, "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def create_password_reset_token(email: str) -> str:
    return _create_token(
        {"sub": email, "type": "password_reset"},
        timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )


def decode_token(token: str) -> TokenData:
    """Decode and validate a JWT. Raises JWTError on any failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, key_hash). Store only the hash."""
    raw = secrets.token_urlsafe(32)
    return raw, _pwd_context.hash(raw)


def verify_api_key(raw: str, hashed: str) -> bool:
    return _pwd_context.verify(raw, hashed)
