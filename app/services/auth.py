import hashlib
from datetime import datetime, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ApiKey, User
from app.core.exceptions import AuthError


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def authenticate(raw_key: str, session: AsyncSession) -> User:
    key_hash = hash_key(raw_key)
    stmt = (
        select(ApiKey)
        .where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        .join(ApiKey.user)
    )
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    if api_key is None or not api_key.user.is_active:
        raise AuthError()
    api_key.last_used_at = datetime.now(UTC)
    await session.commit()
    return api_key.user
