"""User API — API key management and personal usage logs."""
import hashlib
import hmac
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User, ApiKey, UsageLog

router = APIRouter(prefix="/api/user", tags=["user"])


# ============================================================
# Schemas
# ============================================================

class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    key_prefix: str  # first 8 chars + "..." + last 4 chars of key_hash
    label: str
    created_at: str | None
    last_used_at: str | None


class ApiKeyCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    key: str  # full key, shown only once
    label: str
    created_at: str | None


class UsageLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    model: str
    upstream_id: int | None
    tokens_in: int
    tokens_out: int
    cost: float
    status: str
    error_message: str | None
    latency_ms: int | None
    created_at: str | None


# ============================================================
# API Key management
# ============================================================

@router.get("/keys", response_model=list[ApiKeyResponse])
async def list_keys(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """List all API keys for current user (masked)."""
    result = await session.execute(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active.is_(True))
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=k.id,
            key_prefix=_mask_key_hash(k.key_hash),
            label=k.label,
            created_at=k.created_at.isoformat() if k.created_at else None,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]


@router.post("/keys", response_model=ApiKeyCreateResponse)
async def create_key(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Create a new API key. The full key is returned only once."""
    raw_key = secrets.token_hex(24)
    key_hash = hmac.new(
        settings.secret_key.encode(),
        raw_key.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Count existing keys for default label
    count_result = await session.execute(
        select(func.count(ApiKey.id)).where(
            ApiKey.user_id == user.id, ApiKey.is_active.is_(True)
        )
    )
    existing_count = count_result.scalar() or 0
    label = f"key-{existing_count + 1}"

    api_key = ApiKey(user_id=user.id, key_hash=key_hash, label=label)
    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    logger.info("user_api_key_created", user_id=user.id, key_id=api_key.id)
    return ApiKeyCreateResponse(
        id=api_key.id,
        key=f"{settings.api_key_prefix}{raw_key}",
        label=api_key.label,
        created_at=api_key.created_at.isoformat() if api_key.created_at else None,
    )


@router.delete("/keys/{key_id}")
async def delete_key(
    key_id: int,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Delete an API key. Must belong to the current user."""
    api_key = await session.get(ApiKey, key_id)
    if not api_key:
        raise AppError(404, "API Key 不存在")
    if api_key.user_id != user.id:
        raise AppError(403, "无权操作此 API Key")
    await session.delete(api_key)
    await session.commit()
    logger.info("user_api_key_deleted", user_id=user.id, key_id=key_id)
    return {"status": "ok"}


# ============================================================
# Personal usage logs
# ============================================================

@router.get("/logs", response_model=list[UsageLogResponse])
async def list_user_logs(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
):
    """List current user's usage logs, ordered by time descending."""
    offset = (page - 1) * size
    result = await session.execute(
        select(UsageLog)
        .where(UsageLog.user_id == user.id)
        .order_by(desc(UsageLog.created_at))
        .offset(offset)
        .limit(size)
    )
    logs = result.scalars().all()
    return [
        UsageLogResponse(
            id=log_entry.id,
            model=log_entry.model,
            upstream_id=log_entry.upstream_id,
            tokens_in=log_entry.tokens_in,
            tokens_out=log_entry.tokens_out,
            cost=float(log_entry.cost),
            status=log_entry.status,
            error_message=log_entry.error_message,
            latency_ms=log_entry.latency_ms,
            created_at=log_entry.created_at.isoformat() if log_entry.created_at else None,
        )
        for log_entry in logs
    ]


# ============================================================
# Helpers
# ============================================================

def _mask_key_hash(key_hash: str) -> str:
    """Return first 8 chars + ... + last 4 chars of key_hash."""
    if len(key_hash) <= 12:
        return key_hash[:4] + "..." + key_hash[-4:] if len(key_hash) >= 8 else key_hash
    return key_hash[:8] + "..." + key_hash[-4:]
