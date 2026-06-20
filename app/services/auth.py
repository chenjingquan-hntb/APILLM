import hashlib
import hmac
from datetime import datetime, timedelta, UTC
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import ApiKey, User
from app.core.config import settings
from app.core.exceptions import AuthError


def hash_key(raw_key: str) -> str:
    return hmac.new(
        settings.secret_key.encode(),
        raw_key.encode(),
        hashlib.sha256
    ).hexdigest()


async def authenticate(raw_key: str, session: AsyncSession) -> User:
    # Strip API key prefix if present (compatible with unprefixed keys)
    prefix = settings.api_key_prefix
    if prefix and raw_key.startswith(prefix):
        raw_key = raw_key[len(prefix):]

    key_hash = hash_key(raw_key)
    stmt = (
        select(ApiKey)
        .options(selectinload(ApiKey.user))
        .where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
    )
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    if api_key is None or not api_key.user.is_active:
        raise AuthError()

    # Only update last_used_at if more than 60 seconds have passed
    now = datetime.now(UTC)
    if api_key.last_used_at is None or (now - api_key.last_used_at) > timedelta(seconds=60):
        api_key.last_used_at = now
        await session.commit()

    return api_key.user
