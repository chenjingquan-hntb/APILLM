import json
from fastapi import APIRouter
from sqlalchemy import text

from app.services.redis import get_redis, HEALTH_KEY
from app.db.base import engine
from app.core.logging import logger

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health():
    redis_status = "ok"
    db_status = "ok"

    # Redis health check
    try:
        redis_client = await get_redis()
        await redis_client.ping()
    except Exception as e:
        logger.warning("health_redis_failed", error=str(e))
        redis_status = "disconnected"

    # DB health check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.warning("health_db_failed", error=str(e))
        db_status = "disconnected"

    status = "ok" if (redis_status == "ok" and db_status == "ok") else "degraded"

    # Upstream health summary
    upstream_summary = {"total": 0, "healthy": 0, "degraded": 0, "unhealthy": 0}
    try:
        from app.db.base import async_session_factory
        from app.db.repositories.upstream_repo import UpstreamRepository
        async with async_session_factory() as session:
            upstreams = await UpstreamRepository(session).list()
            upstream_summary["total"] = len(upstreams)
            client = await get_redis()
            for u in upstreams:
                try:
                    raw = await client.get(HEALTH_KEY.format(u.id))
                    if raw:
                        state = json.loads(raw) if isinstance(raw, str) else raw
                        h = state.get("status", "healthy")
                    else:
                        h = "healthy"  # no data yet → assume healthy
                except Exception:
                    h = "healthy"
                if h in ("healthy", "degraded", "unhealthy"):
                    upstream_summary[h] += 1
                else:
                    upstream_summary["healthy"] += 1
    except Exception as e:
        logger.warning("health_upstream_summary_failed", error=str(e))

    return {
        "status": status,
        "redis": redis_status,
        "db": db_status,
        "upstreams": upstream_summary,
    }
