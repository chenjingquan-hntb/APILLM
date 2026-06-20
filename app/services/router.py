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


async def select_upstream_by_model(
    upstreams: list[Upstream],
    model: str,
    manual_prices: dict[str, dict[str, float]] | None = None,
) -> Upstream:
    """Select the cheapest enabled upstream for a given model.

    manual_prices: {model_id: {"prompt": float, "completion": float}} from ModelConfig table.
    Manual prices override automatic Redis prices.
    """
    ranked = await rank_upstreams_by_model(upstreams, model, manual_prices)
    return ranked[0]


async def rank_upstreams_by_model(
    upstreams: list[Upstream],
    model: str,
    manual_prices: dict[str, dict[str, float]] | None = None,
) -> list[Upstream]:
    """Sort upstreams by price (cheapest first), then priority (highest first) as tiebreaker.

    Priority of price sources: manual_prices > Redis cache > no data (priority fallback).
    """
    if not upstreams:
        raise NoAvailableUpstreamError()

    # Check manual price for this model (applies equally to all upstreams)
    manual_cost: float | None = None
    if manual_prices and model in manual_prices:
        mp = manual_prices[model]
        if mp.get("prompt") or mp.get("completion"):
            manual_cost = (mp.get("prompt", 0) or 0) + (mp.get("completion", 0) or 0)

    if manual_cost is not None and manual_cost > 0:
        # Manual price applies to all upstreams equally; sort by priority
        logger.debug("route_manual_price", model=model, price=round(manual_cost, 6))
        ranked = sorted(upstreams, key=lambda u: -u.priority)
        return ranked

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

    priced.sort(key=lambda x: (x[1], -x[0].priority))
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
