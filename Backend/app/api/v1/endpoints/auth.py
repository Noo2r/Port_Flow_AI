"""
Authentication endpoints — register, login (form + JSON), token refresh,
logout, whoami, change-password, forgot-password, reset-password, API keys.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.redis_client import (
    blacklist_token,
    delete_reset_token,
    get_reset_token,
    store_reset_token,
)
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.iam import APIKey, User, UserRole
from app.schemas.auth import (
    APIKeyCreate,
    APIKeyCreated,
    APIKeyResponse,
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.services.email_service import send_password_reset_email

router = APIRouter(tags=["Authentication"])


# ── Register ──────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Self-register a new user account (role is always readonly)",
)
async def register(payload: UserRegister, db: DbSession) -> User:
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.READONLY,   # public registration is always readonly; admin assigns roles
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a user with a specific role",
)
async def admin_create_user(
    payload: UserRegister,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    existing = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        is_verified=True,   # admin-created accounts are pre-verified
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Login (OAuth2 form — compatible with /docs Authorize button) ──────────────

@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Login with email + password (OAuth2 form)",
)
async def login_form(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenResponse:
    return await _authenticate(form.username, form.password, db)


# ── Login (JSON body — for frontend clients) ──────────────────────────────────

from pydantic import BaseModel, EmailStr  # noqa: E402


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with JSON body",
)
async def login_json(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return await _authenticate(payload.email, payload.password, db)


async def _authenticate(email: str, password: str, db: AsyncSession) -> TokenResponse:
    user: User | None = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    user.last_login = datetime.now(timezone.utc)
    await db.commit()

    access = create_access_token(user.id, user.email, user.role)
    refresh = create_refresh_token(user.id)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Token refresh ─────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Exchange a refresh token for a new access token",
)
async def refresh_token(payload: RefreshRequest, db: DbSession) -> AccessTokenResponse:
    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    user = await db.get(User, int(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    access = create_access_token(user.id, user.email, user.role)
    return AccessTokenResponse(
        access_token=access,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Invalidate current access token")
async def logout(current_user: CurrentUser) -> None:
    """Blacklist the current user's token by user_id. All active sessions are invalidated."""
    ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await blacklist_token(f"user:{current_user.id}", ttl)


# ── Whoami ────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
async def whoami(current_user: CurrentUser) -> User:
    return current_user


# ── Change password ───────────────────────────────────────────────────────────

@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    if not current_user.hashed_password or not verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()


# ── Forgot password ───────────────────────────────────────────────────────────

@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED, summary="Request a password-reset email")
async def forgot_password(
    payload: ForgotPasswordRequest,
    background: BackgroundTasks,
    db: DbSession,
) -> dict:
    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()

    # Always return 202 to prevent user enumeration
    if user and user.is_active:
        reset_token = create_password_reset_token(user.email)
        await store_reset_token(
            user.email,
            reset_token,
            ttl_seconds=settings.PASSWORD_RESET_EXPIRE_MINUTES * 60,
        )
        background.add_task(send_password_reset_email, user.email, user.full_name, reset_token)

    return {"detail": "If that email exists, a reset link has been sent"}


# ── Reset password ────────────────────────────────────────────────────────────

@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: DbSession) -> None:
    try:
        data = decode_token(payload.token)
    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")

    if data.get("type") != "password_reset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid token type")

    email: str = data["sub"]
    stored = await get_reset_token(email)
    if stored != payload.token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token already used or expired")

    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    user.hashed_password = hash_password(payload.new_password)
    await db.commit()
    await delete_reset_token(email)


# ── API Keys ──────────────────────────────────────────────────────────────────

@router.post("/me/api-keys", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: APIKeyCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> APIKeyCreated:
    raw, key_hash = generate_api_key()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=payload.expires_days)
        if payload.expires_days
        else None
    )
    key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=payload.name,
        expires_at=expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return APIKeyCreated(**key.__dict__, raw_key=raw)


@router.get("/me/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(current_user: CurrentUser, db: DbSession) -> list[APIKey]:
    result = await db.execute(
        select(APIKey).where(APIKey.user_id == current_user.id)
    )
    return result.scalars().all()


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: int, current_user: CurrentUser, db: DbSession) -> None:
    key = await db.get(APIKey, key_id)
    if not key or key.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    key.is_active = False
    await db.commit()


# ── Admin: user management ────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse], summary="[Admin] List all users")
async def list_users(
    current_user: CurrentUser,
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list[User]:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserResponse, summary="[Admin] Update user")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
