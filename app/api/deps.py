from typing import Annotated
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_session
from app.db.models import User
from app.services.auth import authenticate

_bearer = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Security(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    return await authenticate(credentials.credentials, session)
