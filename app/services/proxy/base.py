from abc import ABC, abstractmethod
from typing import AsyncIterator
import httpx
from app.db.models import Upstream
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk
from app.core.exceptions import ProxyError
from app.core.logging import logger

http_client = httpx.AsyncClient(timeout=120.0)


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def auth_header(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


class BaseProxyHandler(ABC):
    def _url(self, upstream: Upstream, path: str) -> str:
        return build_url(upstream.base_url, path)

    def _raise_for_http_error(self, e: Exception, upstream: Upstream) -> None:
        msg = f"[{upstream.name}] "
        if isinstance(e, httpx.HTTPStatusError):
            msg += f"HTTP {e.response.status_code}"
            logger.error("upstream_http_error", upstream=upstream.name, status=e.response.status_code)
        else:
            msg += str(e)
            logger.error("upstream_request_error", upstream=upstream.name, error=str(e))
        raise ProxyError(msg)

    @abstractmethod
    async def forward(self, request: ChatCompletionRequest, upstream: Upstream) -> ChatCompletionResponse: ...

    @abstractmethod
    async def forward_stream(self, request: ChatCompletionRequest, upstream: Upstream) -> AsyncIterator[ChatCompletionChunk]: ...
