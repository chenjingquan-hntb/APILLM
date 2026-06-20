"""Authentication API — login, refresh, logout, user info.

Uses passwordless login: users without password_hash authenticate via API key only.
Users with password_hash use bcrypt password verification.
"""
from datetime import datetime, timedelta, UTC
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_current_user
from app.core.exceptions import AuthError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User, UserSession
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    UserInfo,
)
from app.services.auth import verify_password
from app.services.jwt import (
    create_access_token,
    verify_access_token,
    create_refresh_token,
    hash_refresh_token,
    REFRESH_TOKEN_EXPIRY,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Authenticate with username + password. Returns JWT tokens."""
    stmt = select(User).options(selectinload(User.sessions)).where(
        User.username == body.username,
        User.is_active.is_(True),
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthError("用户名或密码错误")

    # Check password
    if user.password_hash is None:
        raise AuthError("此账户未设置密码，请使用 API Key 访问")

    if not verify_password(body.password, user.password_hash):
        raise AuthError("用户名或密码错误")

    # Create tokens
    access_token = create_access_token(user.id, user.role)
    raw_refresh = create_refresh_token()
    refresh_hash = hash_refresh_token(raw_refresh)

    # Store refresh token session
    now = datetime.now(UTC)
    user_session = UserSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        expires_at=now + timedelta(seconds=REFRESH_TOKEN_EXPIRY),
    )
    session.add(user_session)
    await session.commit()

    logger.info("user_login", username=user.username, role=user.role)
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    """Exchange a refresh token for a new access + refresh token pair."""
    refresh_hash = hash_refresh_token(body.refresh_token)
    now = datetime.now(UTC)

    stmt = (
        select(UserSession)
        .options(selectinload(UserSession.user))
        .where(
            UserSession.refresh_token_hash == refresh_hash,
            UserSession.expires_at > now,
        )
    )
    result = await session.execute(stmt)
    user_session = result.scalar_one_or_none()

    if user_session is None:
        raise AuthError("Refresh token 无效或已过期")

    user = user_session.user
    if not user.is_active:
        raise AuthError("账户已被禁用")

    # Rotate: delete old session, create new
    await session.delete(user_session)

    access_token = create_access_token(user.id, user.role)
    raw_refresh = create_refresh_token()
    new_hash = hash_refresh_token(raw_refresh)

    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=new_hash,
        expires_at=now + timedelta(seconds=REFRESH_TOKEN_EXPIRY),
    )
    session.add(new_session)
    await session.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


@router.post("/logout")
async def logout(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Invalidate a refresh token."""
    refresh_hash = hash_refresh_token(body.refresh_token)
    stmt = select(UserSession).where(UserSession.refresh_token_hash == refresh_hash)
    result = await session.execute(stmt)
    user_session = result.scalar_one_or_none()
    if user_session:
        await session.delete(user_session)
        await session.commit()
    return {"status": "ok"}


@router.get("/me", response_model=UserInfo)
async def me(
    user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """Return current authenticated user info."""
    return UserInfo(
        id=user.id,
        username=user.username,
        role=user.role,
        balance=float(user.balance),
        is_active=user.is_active,
    )
