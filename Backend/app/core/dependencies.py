"""
FastAPI dependency injection — current user, RBAC guards, API-key auth.
Import these into any router that needs authentication or authorization.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import is_token_blacklisted
from app.core.security import decode_token, verify_api_key
from app.database import get_db
from app.models.iam import APIKey, User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

_FORBIDDEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Insufficient permissions",
)


# ── Token extraction & user lookup ────────────────────────────────────────────

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate access token and return the authenticated User."""
    try:
        payload = decode_token(token)
        token_type = payload.get("type")
        if token_type != "access":
            raise _CREDENTIALS_EXCEPTION
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _CREDENTIALS_EXCEPTION
        # Check blacklist (jti field or fallback to token hash)
        jti = payload.get("jti", token[:16])
        if await is_token_blacklisted(jti):
            raise _CREDENTIALS_EXCEPTION
    except JWTError:
        raise _CREDENTIALS_EXCEPTION

    user = await db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION
    return user


async def get_current_verified_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Check your inbox.",
        )
    return user


# ── API-key authentication ─────────────────────────────────────────────────────

async def get_api_key_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """
    Accepts Bearer <api_key_raw>. If the key matches an active APIKey record,
    returns the associated user. Returns None if no credential provided.
    """
    if not credentials:
        return None
    raw_key = credentials.credentials
    # Fetch all active keys for constant-time comparison
    result = await db.execute(
        select(APIKey).where(APIKey.is_active.is_(True))
    )
    keys = result.scalars().all()
    for key_record in keys:
        if verify_api_key(raw_key, key_record.key_hash):
            if key_record.expires_at:
                from datetime import datetime, timezone
                if datetime.now(timezone.utc) > key_record.expires_at:
                    continue
            user = await db.get(User, key_record.user_id)
            if user and user.is_active:
                # Update last_used_at asynchronously
                from datetime import datetime, timezone
                key_record.last_used_at = datetime.now(timezone.utc)
                await db.commit()
                return user
    return None


# ── RBAC role guards ──────────────────────────────────────────────────────────

def require_roles(*roles: UserRole):
    """
    Factory that returns a dependency enforcing the user has one of the given roles.

    Usage::

        @router.get("/admin-only")
        async def endpoint(user: Annotated[User, Depends(require_roles(UserRole.ADMIN))]):
            ...
    """
    async def _guard(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise _FORBIDDEN_EXCEPTION
        return user

    return _guard


# Convenience composites
RequireAdmin = Depends(require_roles(UserRole.ADMIN))
RequirePortManager = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER))
RequireOperations = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.OPERATIONS))
RequireAnalyst = Depends(require_roles(UserRole.ADMIN, UserRole.PORT_MANAGER, UserRole.ANALYST))


# ── Typed dependency aliases (use in route signatures) ────────────────────────
CurrentUser = Annotated[User, Depends(get_current_user)]
VerifiedUser = Annotated[User, Depends(get_current_verified_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
