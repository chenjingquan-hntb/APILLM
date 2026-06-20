import json
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppError, NoAvailableUpstreamError, ProxyError, UpstreamError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User, Upstream, ModelConfig
from app.db.repositories.upstream_repo import UpstreamRepository
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services.redis import cache_mget, HEALTH_KEY
from app.services.router import rank_upstreams_by_model, get_handler
from sqlalchemy import select

router = APIRouter(tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    try:
        upstreams = await UpstreamRepository(session).get_enabled()

        # Load manual prices from ModelConfig
        manual_prices: dict[str, dict[str, float]] = {}
        mc_result = await session.execute(
            select(ModelConfig).where(ModelConfig.is_enabled.is_(True))
        )
        for mc in mc_result.scalars().all():
            if mc.manual_prompt_price or mc.manual_completion_price:
                manual_prices[mc.model_id] = {
                    "prompt": float(mc.manual_prompt_price or 0),
                    "completion": float(mc.manual_completion_price or 0),
                }

        ranked = await rank_upstreams_by_model(upstreams, request.model, manual_prices)

        # Filter out unhealthy upstreams
        health_keys = [HEALTH_KEY.format(u.id) for u in ranked]
        health_states = await cache_mget(health_keys)
        healthy_ranked = []
        unhealthy_ranked = []
        for u, state in zip(ranked, health_states):
            if state and state.get("status") in ("healthy", "degraded"):
                healthy_ranked.append(u)
            else:
                unhealthy_ranked.append(u)
        ranked = healthy_ranked + unhealthy_ranked

        candidates = ranked[:settings.max_retries]

        if request.stream:
            return await _stream_with_failover(request, candidates)

        return await _non_stream_with_failover(request, candidates)
    except AppError:
        raise
    except Exception as e:
        logger.error("chat_unhandled_error", exc_info=True)
        raise UpstreamError(str(e))


async def _non_stream_with_failover(
    request: ChatCompletionRequest,
    upstreams: list[Upstream],
) -> ChatCompletionResponse:
    if not upstreams:
        raise NoAvailableUpstreamError()
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
    if not upstreams:
        raise NoAvailableUpstreamError()
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
            except Exception as e:
                logger.error("stream_generator_error", exc_info=True)
                yield f"data: {json.dumps({'code': 'stream_error', 'message': str(e)})}\n\n"
                if upstream is last:
                    return
        yield f"data: {json.dumps({'code': 'no_upstream', 'message': 'All upstreams exhausted'})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")
