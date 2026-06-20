import json
from typing import Any
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

PRICE_KEY_FMT = "price:{}:{}"  # price:{upstream_id}:{model}
HEALTH_KEY = "health:{}"       # health:{upstream_id}

_pool: aioredis.ConnectionPool | None = None
_client: aioredis.Redis | None = None


async def init_redis() -> None:
    global _pool, _client
    _pool = aioredis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)
    _client = aioredis.Redis(connection_pool=_pool)
    await _client.ping()
    logger.info("redis_connected", url=settings.redis_url)


async def close_redis() -> None:
    global _pool, _client
    if _client:
        await _client.aclose()
        _client = None
    if _pool:
        await _pool.disconnect()
        _pool = None
    logger.info("redis_disconnected")


def get_redis() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis not initialized")
    return _client


async def cache_get(key: str) -> dict | None:
    client = get_redis()
    raw = await client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set(key: str, value: dict, ttl: int | None = None) -> None:
    client = get_redis()
    data = json.dumps(value)
    if ttl is not None:
        await client.setex(key, ttl, data)
    else:
        await client.set(key, data)


async def cache_delete(*keys: str) -> int:
    if not keys:
        return 0
    client = get_redis()
    return await client.delete(*keys)


async def cache_exists(*keys: str) -> int:
    if not keys:
        return 0
    client = get_redis()
    return await client.exists(*keys)


async def cache_mget(keys: list[str]) -> list[dict | None]:
    if not keys:
        return []
    client = get_redis()
    raw = await client.mget(keys)
    return [json.loads(v) if v else None for v in raw]
