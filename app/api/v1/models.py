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

router = APIRouter(tags=["models"])
_models_client = httpx.AsyncClient(timeout=10.0)


async def _fetch_upstream_models(upstream: Upstream) -> list[dict]:
    try:
        resp = await _models_client.get(
            f"{upstream.base_url.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {upstream.api_key}"},
        )
        return resp.json().get("data", [])
    except Exception:
        return []


@router.get("/models", response_model=ModelList)
async def list_models(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ModelList:
    upstreams = await UpstreamRepository(session).get_enabled()
    results = await asyncio.gather(*[_fetch_upstream_models(u) for u in upstreams])
    seen: set[str] = set()
    models: list[ModelCard] = []
    for data in results:
        for m in data:
            if m["id"] not in seen:
                seen.add(m["id"])
                models.append(ModelCard(id=m["id"], created=m.get("created", 0)))
    return ModelList(data=models)
