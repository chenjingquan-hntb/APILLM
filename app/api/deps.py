from typing import Annotated
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User
from app.services.auth import authenticate as api_key_authenticate
from app.services.jwt import verify_access_token

_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Authenticate via JWT access token OR API key.

    - If the token contains exactly two '.' separators (JWT format), verify as JWT.
    - Otherwise, treat as API key (HMAC-SHA256 hash lookup).
    """
    token = credentials.credentials
    if token.count(".") == 2:
        # JWT access token
        return await _authenticate_jwt(token, session)
    else:
        # API key
        return await api_key_authenticate(token, session)


async def _authenticate_jwt(token: str, session: AsyncSession) -> User:
    """Verify JWT access token and return the User."""
    from sqlalchemy import select
    payload = verify_access_token(token)  # raises AuthError on failure
    user_id = payload.get("sub")
    if not user_id:
        from app.core.exceptions import AuthError
        raise AuthError("Token missing subject")
    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        from app.core.exceptions import AuthError
        raise AuthError("User not found or disabled")
    return user


async def require_admin(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Require admin role."""
    from app.core.exceptions import AuthError
    if user.role != "admin":
        raise AuthError("需要管理员权限")
    return user
