import asyncio
from typing import Annotated
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.base import get_session
from app.db.models import User, Upstream
from app.db.repositories.upstream_repo import UpstreamRepository
from app.schemas.openai import ModelCard, ModelList
from app.services.proxy.base import build_url, auth_header
from app.services.redis import cache_mget, PRICE_KEY_FMT, HEALTH_KEY

router = APIRouter(tags=["models"])
_models_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    follow_redirects=False,
)

_FETCH_TIMEOUT = 5.0


async def _fetch_upstream_models(upstream: Upstream) -> tuple[int, list[str]]:
    """Fetch model IDs from an upstream. Returns (upstream_id, [model_ids])."""
    try:
        resp = await _models_client.get(
            build_url(upstream.base_url, "/v1/models"),
            headers=auth_header(upstream.api_key),
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return (upstream.id, [m["id"] for m in data])
    except (httpx.HTTPError, asyncio.TimeoutError):
        return (upstream.id, [])


@router.get("/models", response_model=ModelList)
async def list_models(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ModelList:
    upstreams = await UpstreamRepository(session).get_enabled()
    sem = asyncio.Semaphore(10)

    async def _bounded_fetch(u):
        async with sem:
            return await asyncio.wait_for(_fetch_upstream_models(u), _FETCH_TIMEOUT)

    tasks = [_bounded_fetch(u) for u in upstreams]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build model → upstream_ids mapping
    model_upstreams: dict[str, set[int]] = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        upstream_id, model_ids = result
        for mid in model_ids:
            if mid not in model_upstreams:
                model_upstreams[mid] = set()
            model_upstreams[mid].add(upstream_id)

    # Collect upstream IDs
    all_upstream_ids: set[int] = set()
    for upstream_ids in model_upstreams.values():
        all_upstream_ids.update(upstream_ids)
    upstream_id_list = list(all_upstream_ids)

    # Build model → price lookup
    # For each model, find the cheapest price among its upstreams
    price_map: dict[str, float | None] = {}
    health_map: dict[int, str] = {}  # upstream_id → health status

    try:
        # Fetch health states
        health_keys = [HEALTH_KEY.format(uid) for uid in upstream_id_list]
        health_raw = await cache_mget(health_keys)
        for uid, raw in zip(upstream_id_list, health_raw):
            if raw and isinstance(raw, dict):
                health_map[uid] = raw.get("status", "healthy")
            else:
                health_map[uid] = "healthy"

        # Fetch prices per model
        for model_id, upstream_ids in model_upstreams.items():
            price_keys = [PRICE_KEY_FMT.format(uid, model_id) for uid in upstream_ids]
            prices_raw = await cache_mget(price_keys)
            best_price: float | None = None
            for raw in prices_raw:
                if raw and isinstance(raw, dict):
                    cost = (raw.get("prompt", 0) or 0) + (raw.get("completion", 0) or 0)
                    if cost > 0 and (best_price is None or cost < best_price):
                        best_price = round(cost, 6)
            price_map[model_id] = best_price
    except Exception:
        # Redis unavailable → all prices None, all healthy
        for model_id in model_upstreams:
            price_map.setdefault(model_id, None)
        for uid in upstream_id_list:
            health_map.setdefault(uid, "healthy")

    # Build model cards
    models: list[ModelCard] = []
    for model_id in sorted(model_upstreams.keys()):
        upstream_ids = model_upstreams[model_id]
        # Check availability: at least one upstream is healthy
        available = any(
            health_map.get(uid, "healthy") in ("healthy", "degraded")
            for uid in upstream_ids
        )
        models.append(ModelCard(
            id=model_id,
            upstream_count=len(upstream_ids),
            lowest_price=price_map.get(model_id),
            available=available,
        ))

    return ModelList(data=models)
