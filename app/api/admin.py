"""Admin API — upstreams, models, price management, user management.

All endpoints require admin role.
"""
from datetime import datetime, UTC
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, require_admin
from app.core.exceptions import AppError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import (
    User,
    Upstream,
    UpstreamProtocol,
    ModelConfig,
    UpstreamModelBinding,
    UsageLog,
)
from app.services.price_fetcher import fetch_all, store_pricing
from app.services.health_checker import check_all
from app.services.redis import get_redis, PRICE_KEY_FMT, HEALTH_KEY

router = APIRouter(prefix="/api/admin", tags=["admin"])

# All admin routes require admin role
_admin = Depends(require_admin)
_session = Depends(get_session)


# ============================================================
# Request/Response schemas
# ============================================================

class UpstreamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(max_length=64)
    base_url: str = Field(max_length=256)
    api_key: str = Field(max_length=256)
    protocol: str = Field(default="openai")
    priority: int = 0
    markup_rate: float = 0.2
    is_enabled: bool = True
    pricing_config: dict | None = None


class UpstreamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=64)
    base_url: str | None = Field(None, max_length=256)
    api_key: str | None = Field(None, max_length=256)
    protocol: str | None = None
    priority: int | None = None
    markup_rate: float | None = None
    is_enabled: bool | None = None
    pricing_config: dict | None = None


class ModelConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(max_length=128)
    display_name: str | None = None
    group_name: str | None = None
    description: str | None = None
    icon: str | None = None
    manual_prompt_price: float | None = None
    manual_completion_price: float | None = None
    is_enabled: bool = True
    sort_order: int = 0


class ModelConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = None
    group_name: str | None = None
    description: str | None = None
    icon: str | None = None
    manual_prompt_price: float | None = None
    manual_completion_price: float | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None


class UpstreamModelBind(BaseModel):
    model_config = ConfigDict(extra="forbid")
    upstream_id: int
    model_id: str = Field(max_length=128)


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(max_length=64)
    password: str = Field(max_length=128)
    role: str = "user"


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str | None = Field(None, max_length=64)
    password: str | None = Field(None, max_length=128)
    role: str | None = None
    balance: float | None = None
    is_active: bool | None = None


# ============================================================
# Upstream CRUD
# ============================================================

@router.get("/upstreams")
async def list_upstreams(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    result = await session.execute(select(Upstream).order_by(Upstream.priority.desc()))
    upstreams = result.scalars().all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "base_url": u.base_url,
            "api_key": u.api_key[:8] + "..." if u.api_key else "",
            "protocol": u.protocol.value,
            "priority": u.priority,
            "markup_rate": float(u.markup_rate),
            "is_enabled": u.is_enabled,
            "pricing_config": u.pricing_config,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in upstreams
    ]


@router.post("/upstreams")
async def create_upstream(
    body: UpstreamCreate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    upstream = Upstream(
        name=body.name,
        base_url=body.base_url,
        api_key=body.api_key,
        protocol=UpstreamProtocol(body.protocol),
        priority=body.priority,
        markup_rate=body.markup_rate,
        is_enabled=body.is_enabled,
        pricing_config=body.pricing_config,
    )
    session.add(upstream)
    await session.commit()
    await session.refresh(upstream)
    logger.info("admin_upstream_created", name=upstream.name, admin=admin.username)
    return {"id": upstream.id, "name": upstream.name}


@router.put("/upstreams/{upstream_id}")
async def update_upstream(
    upstream_id: int,
    body: UpstreamUpdate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    upstream = await session.get(Upstream, upstream_id)
    if not upstream:
        raise AppError(404, "上游不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "protocol" and value:
            value = UpstreamProtocol(value)
        setattr(upstream, field, value)
    await session.commit()
    return {"status": "ok"}


@router.delete("/upstreams/{upstream_id}")
async def delete_upstream(
    upstream_id: int,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    upstream = await session.get(Upstream, upstream_id)
    if not upstream:
        raise AppError(404, "上游不存在")
    await session.delete(upstream)
    await session.commit()
    logger.info("admin_upstream_deleted", name=upstream.name, admin=admin.username)
    return {"status": "ok"}


# ============================================================
# Model Config CRUD
# ============================================================

@router.get("/models")
async def list_model_configs(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    result = await session.execute(select(ModelConfig).order_by(ModelConfig.sort_order))
    configs = result.scalars().all()
    return [
        {
            "id": c.id,
            "model_id": c.model_id,
            "display_name": c.display_name,
            "group_name": c.group_name,
            "description": c.description,
            "icon": c.icon,
            "manual_prompt_price": float(c.manual_prompt_price) if c.manual_prompt_price else None,
            "manual_completion_price": float(c.manual_completion_price) if c.manual_completion_price else None,
            "is_enabled": c.is_enabled,
            "sort_order": c.sort_order,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in configs
    ]


@router.post("/models")
async def create_model_config(
    body: ModelConfigCreate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    config = ModelConfig(
        model_id=body.model_id,
        display_name=body.display_name,
        group_name=body.group_name,
        description=body.description,
        icon=body.icon,
        manual_prompt_price=body.manual_prompt_price,
        manual_completion_price=body.manual_completion_price,
        is_enabled=body.is_enabled,
        sort_order=body.sort_order,
    )
    session.add(config)
    await session.commit()
    await session.refresh(config)
    return {"id": config.id, "model_id": config.model_id}


@router.put("/models/{config_id}")
async def update_model_config(
    config_id: int,
    body: ModelConfigUpdate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    config = await session.get(ModelConfig, config_id)
    if not config:
        raise AppError(404, "模型配置不存在")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    config.updated_at = datetime.now(UTC)
    await session.commit()
    return {"status": "ok"}


@router.delete("/models/{config_id}")
async def delete_model_config(
    config_id: int,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    config = await session.get(ModelConfig, config_id)
    if not config:
        raise AppError(404, "模型配置不存在")
    await session.delete(config)
    await session.commit()
    return {"status": "ok"}


# ============================================================
# Model-Upstream binding management
# ============================================================

@router.get("/models/{config_id}/upstreams")
async def list_model_upstreams(
    config_id: int,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    config = await session.get(ModelConfig, config_id)
    if not config:
        raise AppError(404, "模型配置不存在")
    result = await session.execute(
        select(UpstreamModelBinding).where(UpstreamModelBinding.model_id == config.model_id)
    )
    bindings = result.scalars().all()
    return [
        {"id": b.id, "upstream_id": b.upstream_id, "model_id": b.model_id, "is_enabled": b.is_enabled}
        for b in bindings
    ]


@router.post("/models/{config_id}/upstreams")
async def bind_upstream_to_model(
    config_id: int,
    body: UpstreamModelBind,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    config = await session.get(ModelConfig, config_id)
    if not config:
        raise AppError(404, "模型配置不存在")
    binding = UpstreamModelBinding(
        upstream_id=body.upstream_id,
        model_id=config.model_id,
    )
    session.add(binding)
    await session.commit()
    await session.refresh(binding)
    return {"id": binding.id}


@router.delete("/models/{config_id}/upstreams/{binding_id}")
async def unbind_upstream_from_model(
    config_id: int,
    binding_id: int,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    binding = await session.get(UpstreamModelBinding, binding_id)
    if not binding:
        raise AppError(404, "绑定不存在")
    await session.delete(binding)
    await session.commit()
    return {"status": "ok"}


# ============================================================
# Price management
# ============================================================

@router.post("/prices/fetch")
async def trigger_price_fetch(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    """Manually trigger upstream price fetching."""
    try:
        pricing = await fetch_all(session)
        if pricing:
            await store_pricing(pricing)
        return {"status": "ok", "upstreams_fetched": len(pricing)}
    except Exception as e:
        logger.error("admin_price_fetch_failed", error=str(e))
        raise AppError(500, f"价格抓取失败: {e}")


@router.get("/prices")
async def list_prices(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
    model: str = Query(None, description="Filter by model name"),
):
    """List all cached prices from Redis."""
    upstreams = await session.execute(select(Upstream))
    upstreams = upstreams.scalars().all()
    client = await get_redis()

    results = []
    for u in upstreams:
        # Scan for price keys: price:{upstream_id}:*
        cursor = 0
        pattern = f"price:{u.id}:*"
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            for key in keys:
                raw = await client.get(key)
                if raw:
                    import json
                    data = json.loads(raw)
                    parts = key.split(":")
                    model_id = ":".join(parts[2:]) if len(parts) > 2 else parts[-1]
                    if model and model not in model_id:
                        continue
                    results.append({
                        "upstream_id": u.id,
                        "upstream_name": u.name,
                        "model": model_id,
                        "prompt": data.get("prompt"),
                        "completion": data.get("completion"),
                        "updated_at": data.get("updated_at"),
                    })
            if cursor == 0:
                break

    return {"prices": results}


# ============================================================
# User management (admin)
# ============================================================

@router.get("/users")
async def list_users(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "balance": float(u.balance),
            "is_active": u.is_active,
            "has_password": u.password_hash is not None,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users")
async def create_user(
    body: UserCreate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    from app.services.auth import hash_password
    password_hash = hash_password(body.password)
    user = User(
        username=body.username,
        password_hash=password_hash,
        role=body.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("admin_user_created", username=user.username, role=user.role, admin=admin.username)
    return {"id": user.id, "username": user.username, "role": user.role}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdate,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    user = await session.get(User, user_id)
    if not user:
        raise AppError(404, "用户不存在")
    update_data = body.model_dump(exclude_unset=True)
    if "password" in update_data:
        from app.services.auth import hash_password
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(user, field, value)
    await session.commit()
    return {"status": "ok"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    if user_id == admin.id:
        raise AppError(400, "不能删除自己")
    user = await session.get(User, user_id)
    if not user:
        raise AppError(404, "用户不存在")
    await session.delete(user)
    await session.commit()
    logger.info("admin_user_deleted", username=user.username, admin=admin.username)
    return {"status": "ok"}


# ============================================================
# Health trigger
# ============================================================

@router.post("/health/check")
async def trigger_health_check(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    """Manually trigger upstream health check."""
    try:
        await check_all(session)
        return {"status": "ok"}
    except Exception as e:
        logger.error("admin_health_check_failed", error=str(e))
        raise AppError(500, f"健康检查失败: {e}")


# ============================================================
# Usage logs (admin)
# ============================================================

@router.get("/logs")
async def admin_list_logs(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    model: str | None = Query(None),
    status: str | None = Query(None),
):
    q = select(UsageLog)
    if user_id:
        q = q.where(UsageLog.user_id == user_id)
    if model:
        q = q.where(UsageLog.model == model)
    if status:
        q = q.where(UsageLog.status == status)
    offset = (page - 1) * size
    result = await session.execute(
        q.order_by(desc(UsageLog.created_at)).offset(offset).limit(size)
    )
    logs = result.scalars().all()
    total_result = await session.execute(select(func.count()).select_from(q.alias()))
    total = total_result.scalar_one()
    return {
        "total": total,
        "page": page,
        "size": size,
        "data": [
            {
                "id": log_entry.id,
                "user_id": log_entry.user_id,
                "model": log_entry.model,
                "upstream_id": log_entry.upstream_id,
                "tokens_in": log_entry.tokens_in,
                "tokens_out": log_entry.tokens_out,
                "cost": float(log_entry.cost),
                "status": log_entry.status,
                "error_message": log_entry.error_message,
                "latency_ms": log_entry.latency_ms,
                "created_at": log_entry.created_at.isoformat() if log_entry.created_at else None,
            }
            for log_entry in logs
        ],
    }


# ============================================================
# Stats dashboard (admin)
# ============================================================

@router.get("/stats/overview")
async def admin_stats_overview(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    from datetime import datetime, timedelta, UTC
    since = datetime.now(UTC) - timedelta(hours=24)
    result = await session.execute(
        select(
            func.count(UsageLog.id).label("calls"),
            func.sum(UsageLog.tokens_in).label("tokens_in"),
            func.sum(UsageLog.tokens_out).label("tokens_out"),
            func.sum(UsageLog.cost).label("cost"),
        ).where(UsageLog.created_at >= since, UsageLog.status == "success")
    )
    row = result.one()
    active_users_result = await session.execute(
        select(func.count(func.distinct(UsageLog.user_id))).where(
            UsageLog.created_at >= since
        )
    )
    active_users = active_users_result.scalar_one()
    return {
        "total_calls_24h": row.calls or 0,
        "total_tokens_in_24h": row.tokens_in or 0,
        "total_tokens_out_24h": row.tokens_out or 0,
        "total_cost_24h": float(row.cost or 0),
        "active_users_24h": active_users or 0,
    }


@router.get("/stats/by-model")
async def admin_stats_by_model(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    result = await session.execute(
        select(
            UsageLog.model,
            func.count(UsageLog.id).label("calls"),
            func.sum(UsageLog.tokens_in).label("tokens_in"),
            func.sum(UsageLog.tokens_out).label("tokens_out"),
            func.sum(UsageLog.cost).label("cost"),
        ).where(UsageLog.status == "success").group_by(UsageLog.model).order_by(desc(func.count(UsageLog.id)))
    )
    return [
        {
            "model": r.model,
            "calls": r.calls,
            "tokens_in": r.tokens_in or 0,
            "tokens_out": r.tokens_out or 0,
            "cost": float(r.cost or 0),
        }
        for r in result.all()
    ]


@router.get("/stats/by-upstream")
async def admin_stats_by_upstream(
    session: Annotated[AsyncSession, _session],
    admin: Annotated[User, _admin],
):
    result = await session.execute(
        select(
            UsageLog.upstream_id,
            func.count(UsageLog.id).label("calls"),
            func.sum(UsageLog.tokens_in).label("tokens_in"),
            func.sum(UsageLog.tokens_out).label("tokens_out"),
            func.sum(UsageLog.cost).label("cost"),
        ).where(UsageLog.status == "success").group_by(UsageLog.upstream_id).order_by(desc(func.count(UsageLog.id)))
    )
    return [
        {
            "upstream_id": r.upstream_id,
            "calls": r.calls,
            "tokens_in": r.tokens_in or 0,
            "tokens_out": r.tokens_out or 0,
            "cost": float(r.cost or 0),
        }
        for r in result.all()
    ]
