from app.db.models import Upstream, UpstreamProtocol
from app.services.proxy.base import BaseProxyHandler
from app.services.proxy.openai_proxy import OpenAIProxyHandler
from app.services.proxy.anthropic_proxy import AnthropicProxyHandler
from app.core.exceptions import NoAvailableUpstreamError
from app.core.logging import logger
from app.services.redis import cache_mget, PRICE_KEY_FMT

_HANDLERS: dict[UpstreamProtocol, BaseProxyHandler] = {
    UpstreamProtocol.openai: OpenAIProxyHandler(),
    UpstreamProtocol.anthropic: AnthropicProxyHandler(),
}


def get_handler(upstream: Upstream) -> BaseProxyHandler:
    handler = _HANDLERS.get(upstream.protocol)
    if handler is None:
        raise NoAvailableUpstreamError()
    return handler


def select_upstream(upstreams: list[Upstream]) -> Upstream:
    """Select the upstream with the highest priority."""
    if not upstreams:
        raise NoAvailableUpstreamError()
    return max(upstreams, key=lambda u: u.priority)


async def select_upstream_by_model(upstreams: list[Upstream], model: str) -> Upstream:
    """Select the cheapest enabled upstream for a given model.

    Reads price cache from Redis. Falls back to priority-based selection
    if no price data is available for the model.
    """
    ranked = await rank_upstreams_by_model(upstreams, model)
    return ranked[0]


async def rank_upstreams_by_model(upstreams: list[Upstream], model: str) -> list[Upstream]:
    """Sort upstreams by price (cheapest first), then priority (highest first) as tiebreaker.

    Upstreams without price data are placed after priced ones, sorted by priority.
    """
    if not upstreams:
        raise NoAvailableUpstreamError()

    keys = [PRICE_KEY_FMT.format(u.id, model) for u in upstreams]
    try:
        prices = await cache_mget(keys)
    except Exception:
        logger.warning("redis_unavailable_in_router", model=model)
        prices = [None] * len(keys)

    priced: list[tuple[Upstream, float]] = []
    unpriced: list[Upstream] = []

    for upstream, price_data in zip(upstreams, prices):
        if price_data and (price_data.get("prompt") or price_data.get("completion")):
            cost = price_data["prompt"] + price_data["completion"]
            priced.append((upstream, cost))
        else:
            unpriced.append(upstream)

    # Sort by cost ascending, then priority descending as tiebreaker
    priced.sort(key=lambda x: (x[1], -x[0].priority))
    # Unpriced sorted by priority descending
    unpriced.sort(key=lambda u: -u.priority)

    ranked = [u for u, _ in priced] + unpriced

    if priced:
        logger.debug(
            "smart_route",
            model=model,
            best=ranked[0].name,
            price=round(priced[0][1], 6),
            candidates=len(priced),
        )
    else:
        logger.debug("route_fallback_priority", model=model, upstreams=[u.name for u in ranked])

    return ranked
