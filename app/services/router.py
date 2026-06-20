from app.db.models import Upstream, UpstreamProtocol
from app.services.proxy.base import BaseProxyHandler
from app.services.proxy.openai_proxy import OpenAIProxyHandler
from app.services.proxy.anthropic_proxy import AnthropicProxyHandler
from app.core.exceptions import NoAvailableUpstreamError

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
    if not upstreams:
        raise NoAvailableUpstreamError()
    return max(upstreams, key=lambda u: u.priority)
