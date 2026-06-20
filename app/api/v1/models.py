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

router = APIRouter(tags=["models"])
_models_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=5.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    follow_redirects=False,
)

_FETCH_TIMEOUT = 5.0


async def _fetch_upstream_models(upstream: Upstream) -> list[dict]:
    try:
        resp = await _models_client.get(
            build_url(upstream.base_url, "/v1/models"),
            headers=auth_header(upstream.api_key),
        )
        resp.raise_for_status()
        return resp.json().get("data", [])
    except (httpx.HTTPError, asyncio.TimeoutError):
        return []


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
    seen: set[str] = set()
    models: list[ModelCard] = []
    for data in results:
        if isinstance(data, Exception):
            continue
        for m in data:
            if m["id"] not in seen:
                seen.add(m["id"])
                models.append(ModelCard(id=m["id"], created=m.get("created", 0)))
    return ModelList(data=models)
