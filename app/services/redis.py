import json
import time
from typing import Any
from urllib.parse import urlparse
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

PRICE_KEY_FMT = "price:{}:{}"  # price:{upstream_id}:{model}
HEALTH_KEY = "health:{}"       # health:{upstream_id}

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None

_last_reconnect_attempt: float = 0.0
_RECONNECT_COOLDOWN = 5.0  # seconds between reconnect attempts


def _sanitize_redis_url(url: str) -> str:
    """Extract host:port from Redis URL, hiding password."""
    try:
        parsed = urlparse(url)
        return f"{parsed.hostname}:{parsed.port or 6379}"
    except Exception:
        return "<unknown>"


async def init_redis() -> bool:
    """Initialize Redis connection pool. Returns True on success, False on failure."""
    global _pool, _client
    try:
        _pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
        _client = aioredis.Redis(connection_pool=_pool)
        await _client.ping()
        logger.info("redis_connected", host=_sanitize_redis_url(settings.redis_url))
        return True
    except Exception as e:
        logger.warning("redis_init_failed", error=str(e), url=_sanitize_redis_url(settings.redis_url))
        _client = None
        if _pool:
            try:
                await _pool.disconnect()
            except Exception:
                pass
            _pool = None
        return False


async def close_redis() -> None:
    global _pool, _client
    if _client:
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
    if _pool:
        try:
            await _pool.disconnect()
        except Exception:
            pass
        _pool = None
    logger.info("redis_disconnected")


async def get_redis() -> aioredis.Redis:
    global _client, _pool, _last_reconnect_attempt

    # Cooldown guard: avoid reconnect storm when Redis is down
    now = time.monotonic()
    if _client is None and now - _last_reconnect_attempt < _RECONNECT_COOLDOWN:
        raise RuntimeError("Redis not initialized (cooldown)")

    if _client is None:
        _last_reconnect_attempt = now
        ok = await init_redis()
        if not ok:
            raise RuntimeError("Redis not initialized")
        return _client

    try:
        await _client.ping()
    except Exception:
        logger.warning("redis_health_check_failed", extra={"action": "reconnecting"})
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
        if _pool:
            try:
                await _pool.disconnect()
            except Exception:
                pass
            _pool = None
        _last_reconnect_attempt = time.monotonic()
        ok = await init_redis()
        if not ok:
            raise RuntimeError("Redis not initialized")
    return _client


async def cache_get(key: str) -> Any | None:
    try:
        client = await get_redis()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
        return None


async def cache_set(key: str, value: dict, ttl: int | None = None) -> None:
    try:
        client = await get_redis()
        data = json.dumps(value)
        if ttl is not None:
            await client.setex(key, ttl, data)
        else:
            await client.set(key, data)
    except Exception as e:
        logger.warning("cache_set_failed", key=key, error=str(e))


async def cache_delete(*keys: str) -> int:
    if not keys:
        return 0
    try:
        client = await get_redis()
        return await client.delete(*keys)
    except Exception as e:
        logger.warning("cache_delete_failed", keys=keys, error=str(e))
        return 0


async def cache_exists(*keys: str) -> int:
    if not keys:
        return 0
    try:
        client = await get_redis()
        return await client.exists(*keys)
    except Exception as e:
        logger.warning("cache_exists_failed", keys=keys, error=str(e))
        return 0


async def cache_mget(keys: list[str]) -> list[Any | None]:
    if not keys:
        return []
    try:
        client = await get_redis()
        raw = await client.mget(keys)
        return [json.loads(v) if v else None for v in raw]
    except Exception as e:
        logger.warning("cache_mget_failed", keys=keys, error=str(e))
        return []
