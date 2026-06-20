import json
import time
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.exceptions import AppError, NoAvailableUpstreamError, ProxyError, UpstreamError
from app.core.logging import logger
from app.db.base import get_session
from app.db.models import User, Upstream, ModelConfig, UsageLog
from app.db.repositories.upstream_repo import UpstreamRepository
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services.redis import cache_mget, HEALTH_KEY
from app.services.router import rank_upstreams_by_model, get_handler

router = APIRouter(tags=["chat"])


def _build_manual_prices(session_result) -> dict[str, dict[str, float]]:
    """Helper: extract manual prices from ModelConfig rows."""
    mp: dict[str, dict[str, float]] = {}
    for mc in session_result:
        if mc.manual_prompt_price or mc.manual_completion_price:
            mp[mc.model_id] = {
                "prompt": float(mc.manual_prompt_price or 0),
                "completion": float(mc.manual_completion_price or 0),
            }
    return mp


def _filter_healthy(ranked: list[Upstream], health_states: list) -> list[Upstream]:
    healthy = []
    unhealthy = []
    for u, state in zip(ranked, health_states):
        if state and state.get("status") in ("healthy", "degraded"):
            healthy.append(u)
        else:
            unhealthy.append(u)
    return healthy + unhealthy


async def _record_usage_log(
    session: AsyncSession,
    user_id: int,
    model: str,
    upstream_id: int | None,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    status: str,
    error_message: str | None,
    latency_ms: int,
):
    """Write a UsageLog entry. Never raises outside."""
    try:
        log = UsageLog(
            user_id=user_id,
            model=model,
            upstream_id=upstream_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        session.add(log)
        await session.commit()
    except Exception as e:
        logger.warning("usage_log_write_failed", error=str(e))


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    start_time = time.time()
    status = "error"
    error_detail: str | None = None
    used_upstream_id: int | None = None

    try:
        upstreams = await UpstreamRepository(session).get_enabled()

        # Load manual prices from ModelConfig
        mc_result = await session.execute(
            select(ModelConfig).where(ModelConfig.is_enabled.is_(True))
        )
        manual_prices = _build_manual_prices(mc_result.scalars().all())

        ranked = await rank_upstreams_by_model(upstreams, request.model, manual_prices)

        # Filter out unhealthy upstreams
        health_keys = [HEALTH_KEY.format(u.id) for u in ranked]
        health_states = await cache_mget(health_keys)
        ranked = _filter_healthy(ranked, health_states)

        candidates = ranked[:settings.max_retries]

        if request.stream:
            return await _stream_with_failover(request, candidates, user, session, start_time)

        response, used_upstream_id = await _non_stream_with_failover(request, candidates)
        status = "success"

        # Log usage for non-stream
        latency_ms = int((time.time() - start_time) * 1000)
        usage = response.usage
        await _record_usage_log(
            session=session,
            user_id=user.id,
            model=request.model,
            upstream_id=used_upstream_id,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            cost=0.0,
            status="success",
            error_message=None,
            latency_ms=latency_ms,
        )

        return response

    except AppError as e:
        error_detail = str(getattr(e, "detail", str(e)))
        raise
    except Exception as e:
        error_detail = str(e)
        logger.error("chat_unhandled_error", exc_info=True)
        raise UpstreamError(error_detail)
    finally:
        # Always record error if we didn't succeed
        if status == "error" and error_detail is not None:
            latency_ms = int((time.time() - start_time) * 1000)
            await _record_usage_log(
                session=session,
                user_id=user.id,
                model=request.model,
                upstream_id=used_upstream_id,
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                status="error",
                error_message=error_detail[:500],
                latency_ms=latency_ms,
            )


async def _non_stream_with_failover(
    request: ChatCompletionRequest,
    upstreams: list[Upstream],
) -> tuple[ChatCompletionResponse, int]:
    """Forward request to upstreams in order. Returns (response, upstream_id)."""
    if not upstreams:
        raise NoAvailableUpstreamError()
    errors: list[str] = []
    for upstream in upstreams:
        handler = get_handler(upstream)
        try:
            response = await handler.forward(request, upstream)
            return response, upstream.id
        except ProxyError as e:
            errors.append(f"[{upstream.name}] {e.detail}")
            logger.warning("failover_try_next", upstream=upstream.name, model=request.model)
    raise UpstreamError("; ".join(errors))


async def _stream_with_failover(
    request: ChatCompletionRequest,
    upstreams: list[Upstream],
    user: User | None = None,
    session: AsyncSession | None = None,
    start_time: float | None = None,
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
                # Log success for stream
                if session is not None and user is not None:
                    latency_ms = int((time.time() - start_time) * 1000) if start_time else None
                    await _record_usage_log(
                        session=session,
                        user_id=user.id,
                        model=request.model,
                        upstream_id=upstream.id,
                        tokens_in=0,
                        tokens_out=0,
                        cost=0.0,
                        status="success",
                        error_message=None,
                        latency_ms=latency_ms or 0,
                    )
                return
            except ProxyError as e:
                logger.warning("failover_try_next_stream", upstream=upstream.name, model=request.model)
                if upstream is last:
                    yield f"data: {json.dumps({'code': 'upstream_error', 'message': e.detail})}\n\n"
                    # Log error for last upstream
                    if session is not None and user is not None:
                        latency_ms = int((time.time() - start_time) * 1000) if start_time else None
                        await _record_usage_log(
                            session=session,
                            user_id=user.id,
                            model=request.model,
                            upstream_id=upstream.id,
                            tokens_in=0,
                            tokens_out=0,
                            cost=0.0,
                            status="error",
                            error_message=e.detail,
                            latency_ms=latency_ms or 0,
                        )
            except Exception as e:
                logger.error("stream_generator_error", exc_info=True)
                yield f"data: {json.dumps({'code': 'stream_error', 'message': str(e)})}\n\n"
                if upstream is last:
                    # Log unexpected error
                    if session is not None and user is not None:
                        latency_ms = int((time.time() - start_time) * 1000) if start_time else None
                        await _record_usage_log(
                            session=session,
                            user_id=user.id,
                            model=request.model,
                            upstream_id=upstream.id,
                            tokens_in=0,
                            tokens_out=0,
                            cost=0.0,
                            status="error",
                            error_message=str(e),
                            latency_ms=latency_ms or 0,
                        )
                    return
        yield f"data: {json.dumps({'code': 'no_upstream', 'message': 'All upstreams exhausted'})}\n\n"
        # Log exhaustion
        if session is not None and user is not None:
            latency_ms = int((time.time() - start_time) * 1000) if start_time else None
            await _record_usage_log(
                session=session,
                user_id=user.id,
                model=request.model,
                upstream_id=None,
                tokens_in=0,
                tokens_out=0,
                cost=0.0,
                status="error",
                error_message="All upstreams exhausted",
                latency_ms=latency_ms or 0,
            )

    return StreamingResponse(_stream(), media_type="text/event-stream")
