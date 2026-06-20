import json
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import ProxyError, UpstreamError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User, Upstream
from app.db.repositories.upstream_repo import UpstreamRepository
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services.router import rank_upstreams_by_model, get_handler

router = APIRouter(tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    upstreams = await UpstreamRepository(session).get_enabled()
    ranked = await rank_upstreams_by_model(upstreams, request.model)
    candidates = ranked[:settings.max_retries]

    if request.stream:
        return await _stream_with_failover(request, candidates)

    return await _non_stream_with_failover(request, candidates)


async def _non_stream_with_failover(
    request: ChatCompletionRequest,
    upstreams: list[Upstream],
) -> ChatCompletionResponse:
    errors: list[str] = []
    for upstream in upstreams:
        handler = get_handler(upstream)
        try:
            return await handler.forward(request, upstream)
        except ProxyError as e:
            errors.append(f"[{upstream.name}] {e.detail}")
            logger.warning("failover_try_next", upstream=upstream.name, model=request.model)
    raise UpstreamError("; ".join(errors))


async def _stream_with_failover(
    request: ChatCompletionRequest,
    upstreams: list[Upstream],
) -> StreamingResponse:
    last = upstreams[-1] if upstreams else None

    async def _stream():
        for upstream in upstreams:
            handler = get_handler(upstream)
            try:
                async for chunk in handler.forward_stream(request, upstream):
                    yield f"data: {chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                return
            except ProxyError as e:
                logger.warning("failover_try_next_stream", upstream=upstream.name, model=request.model)
                if upstream is last:
                    yield f"data: {json.dumps({'code': 'upstream_error', 'message': e.detail})}\n\n"
        yield f"data: {json.dumps({'code': 'no_upstream', 'message': 'All upstreams exhausted'})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
