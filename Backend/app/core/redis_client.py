"""
Async Redis client — token blacklist, session store, rate-limit counters.
Falls back gracefully when Redis is unavailable (logs warning, no crash).
"""
from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a shared Redis connection pool, or None if unavailable."""
    global _pool
    if _pool is None:
        try:
            _pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await _pool.ping()
            logger.info("Redis connected: %s", settings.REDIS_URL)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — token blacklist disabled", exc)
            _pool = None
    return _pool


async def close_redis() -> None:
    global _pool
    if _pool:
        await _pool.aclose()
        _pool = None


# ── Token blacklist ───────────────────────────────────────────────────────────

_BLACKLIST_PREFIX = "bl:"
_SESSION_PREFIX = "sess:"


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Mark a JWT jti (or full token hash) as revoked."""
    redis = await get_redis()
    if redis:
        await redis.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")


async def is_token_blacklisted(jti: str) -> bool:
    redis = await get_redis()
    if redis is None:
        return False
    return bool(await redis.exists(f"{_BLACKLIST_PREFIX}{jti}"))


# ── Password-reset OTP store ──────────────────────────────────────────────────

_RESET_PREFIX = "pwreset:"


async def store_reset_token(email: str, token: str, ttl_seconds: int = 900) -> None:
    redis = await get_redis()
    if redis:
        await redis.setex(f"{_RESET_PREFIX}{email}", ttl_seconds, token)


async def get_reset_token(email: str) -> str | None:
    redis = await get_redis()
    if redis is None:
        return None
    return await redis.get(f"{_RESET_PREFIX}{email}")


async def delete_reset_token(email: str) -> None:
    redis = await get_redis()
    if redis:
        await redis.delete(f"{_RESET_PREFIX}{email}")


# ── Generic cache helpers ─────────────────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    redis = await get_redis()
    if redis:
        await redis.setex(key, ttl_seconds, str(value))


async def cache_get(key: str) -> str | None:
    redis = await get_redis()
    if redis is None:
        return None
    return await redis.get(key)


async def cache_delete(key: str) -> None:
    redis = await get_redis()
    if redis:
        await redis.delete(key)
