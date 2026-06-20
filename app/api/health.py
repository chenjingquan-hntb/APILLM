from fastapi import APIRouter
from sqlalchemy import text

from app.services.redis import get_redis
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
    return {"status": status, "redis": redis_status, "db": db_status}
