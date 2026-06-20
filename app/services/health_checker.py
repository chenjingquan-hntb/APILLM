import asyncio
import time
import enum
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.db.models import Upstream
from app.db.repositories.upstream_repo import UpstreamRepository
from app.services.proxy.base import build_url, auth_header
from app.services.redis import cache_get, cache_set, HEALTH_KEY

_health_client = httpx.AsyncClient(timeout=5.0)


class HealthStatus(str, enum.Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"


async def _ping_upstream(upstream: Upstream) -> bool:
    try:
        resp = await _health_client.get(
            build_url(upstream.base_url, "/v1/models"),
            headers=auth_header(upstream.api_key),
        )
        resp.raise_for_status()
        return True
    except (httpx.HTTPError, asyncio.TimeoutError):
        return False


async def _update_health(upstream: Upstream, ok: bool) -> bool:
    """Update health state for a single upstream. Returns True if DB change needed."""
    key = HEALTH_KEY.format(upstream.id)
    state = await cache_get(key) or {
        "status": HealthStatus.healthy,
        "consecutive_failures": 0,
        "consecutive_successes": 0,
        "last_check": 0,
    }

    if ok:
        state["consecutive_successes"] += 1
        state["consecutive_failures"] = 0
    else:
        state["consecutive_failures"] += 1
        state["consecutive_successes"] = 0

    state["last_check"] = int(time.time())

    prev_status = state["status"]

    if state["consecutive_failures"] >= settings.failure_threshold:
        state["status"] = HealthStatus.unhealthy
    elif state["consecutive_failures"] >= 1:
        state["status"] = HealthStatus.degraded
    elif state["consecutive_successes"] >= settings.recovery_threshold:
        state["status"] = HealthStatus.healthy

    new_status = state["status"]
    await cache_set(key, state)

    if prev_status != new_status:
        logger.warning(
            "upstream_health_changed",
            upstream=upstream.name,
            prev=prev_status,
            new=new_status,
            consecutive_failures=state["consecutive_failures"],
        )

    return (
        (new_status == HealthStatus.unhealthy and upstream.is_enabled) or
        (new_status == HealthStatus.healthy and not upstream.is_enabled)
    )


async def check_all(session: AsyncSession) -> None:
    """Ping all upstreams concurrently and update health states."""
    all_upstreams = await UpstreamRepository(session).list()
    if not all_upstreams:
        return

    tasks = [asyncio.wait_for(_ping_upstream(u), timeout=5.0) for u in all_upstreams]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    db_changed = False
    for upstream, result in zip(all_upstreams, results):
        ok = result is True
        try:
            needs_db = await _update_health(upstream, ok)
            if needs_db:
                upstream.is_enabled = not upstream.is_enabled
                label = "enabled" if upstream.is_enabled else "disabled"
                logger.warning("upstream_%s", label, upstream=upstream.name)
                db_changed = True
        except Exception:
            logger.error("health_update_error", upstream=upstream.name, exc_info=True)

    if db_changed:
        await session.commit()


async def run_health_loop(session_factory) -> None:
    logger.info("health_loop_started", interval=settings.health_check_interval)
    while True:
        try:
            await asyncio.sleep(settings.health_check_interval)
            async with session_factory() as session:
                await check_all(session)
        except asyncio.CancelledError:
            logger.info("health_loop_cancelled")
            return
        except Exception:
            logger.error("health_loop_error", exc_info=True)


async def close_health_client() -> None:
    await _health_client.aclose()
