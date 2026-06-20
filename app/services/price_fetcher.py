import json
import time
import asyncio
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.db.models import Upstream
from app.db.repositories.upstream_repo import UpstreamRepository
from app.services.proxy.base import build_url, auth_header
from app.services.redis import get_redis, PRICE_KEY_FMT

_price_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=8.0, write=10.0, pool=5.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    follow_redirects=False,
)


def _nested_get(d: dict, path: str) -> float | str | None:
    parts = path.split(".")
    current = d
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


async def _fetch_one(upstream: Upstream) -> list[dict]:
    config = upstream.pricing_config
    if not config:
        return []

    model_field = config.get("model_id_field", "id")
    prompt_field = config.get("prompt_price_field", "")
    completion_field = config.get("completion_price_field", "")

    try:
        resp = await _price_client.get(
            build_url(upstream.base_url, "/v1/models"),
            headers=auth_header(upstream.api_key),
        )
        resp.raise_for_status()
        models_data: list[dict] = resp.json().get("data", [])
    except (httpx.HTTPError, asyncio.TimeoutError):
        logger.warning("price_fetch_failed", upstream=upstream.name, exc_info=True)
        return []

    results: list[dict] = []
    for entry in models_data:
        model_id = _nested_get(entry, model_field)
        if model_id is None:
            continue
        prompt_price = _nested_get(entry, prompt_field) if prompt_field else 0.0
        completion_price = _nested_get(entry, completion_field) if completion_field else 0.0
        try:
            results.append({
                "model": str(model_id),
                "prompt": float(prompt_price) if prompt_price else 0.0,
                "completion": float(completion_price) if completion_price else 0.0,
            })
        except (ValueError, TypeError):
            continue

    logger.info("price_fetch_ok", upstream=upstream.name, models_count=len(results))
    return results


async def fetch_all(session: AsyncSession) -> dict[int, list[dict]]:
    upstreams = await UpstreamRepository(session).get_enabled()
    if not upstreams:
        return {}

    sem = asyncio.Semaphore(10)

    async def _bounded_fetch_one(u):
        async with sem:
            return await _fetch_one(u)

    tasks = [_bounded_fetch_one(u) for u in upstreams]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    pricing: dict[int, list[dict]] = {}
    for upstream, result in zip(upstreams, results):
        if isinstance(result, Exception):
            logger.warning("price_fetch_timeout", upstream=upstream.name)
            continue
        pricing[upstream.id] = result
    return pricing


async def store_pricing(pricing: dict[int, list[dict]]) -> None:
    now = int(time.time())
    ttl = settings.price_cache_ttl
    client = await get_redis()
    pipe = client.pipeline()

    for upstream_id, models in pricing.items():
        for entry in models:
            key = PRICE_KEY_FMT.format(upstream_id, entry["model"])
            value = json.dumps({
                "prompt": entry["prompt"],
                "completion": entry["completion"],
                "currency": "CNY",
                "updated_at": now,
            })
            if ttl:
                pipe.setex(key, ttl, value)
            else:
                pipe.set(key, value)

    await pipe.execute()


async def run_price_fetch_loop(session_factory) -> None:
    logger.info("price_loop_started", interval=settings.price_fetch_interval)
    while True:
        try:
            async with session_factory() as session:
                pricing = await fetch_all(session)
                if pricing:
                    await store_pricing(pricing)
            await asyncio.sleep(settings.price_fetch_interval)
        except asyncio.CancelledError:
            logger.info("price_loop_cancelled")
            return
        except (httpx.HTTPError, asyncio.TimeoutError):
            logger.error("price_loop_error", exc_info=True)
            await asyncio.sleep(settings.price_fetch_interval)


async def close_price_client() -> None:
    await _price_client.aclose()
