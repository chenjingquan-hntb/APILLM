import json
import time
import uuid
from typing import AsyncIterator
import httpx
from pydantic import ValidationError
from app.db.models import Upstream
from app.core.logging import logger
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk, StreamChoice, DeltaMessage
from app.schemas.anthropic import AnthropicResponse, openai_to_anthropic, anthropic_to_openai, STOP_REASON_MAP
from app.services.proxy.base import BaseProxyHandler, http_client

_ANTHROPIC_VERSION = "2023-06-01"


def _headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_VERSION}


class AnthropicProxyHandler(BaseProxyHandler):
    async def forward(self, request: ChatCompletionRequest, upstream: Upstream) -> ChatCompletionResponse:
        payload = openai_to_anthropic(request)
        try:
            resp = await http_client.post(
                self._url(upstream, "/v1/messages"),
                headers=_headers(upstream.api_key),
                json=payload.model_dump(exclude_none=True),
            )
            resp.raise_for_status()
            return anthropic_to_openai(AnthropicResponse.model_validate(resp.json()), request.model)
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValidationError) as e:
            self._raise_for_http_error(e, upstream)

    async def forward_stream(
        self, request: ChatCompletionRequest, upstream: Upstream
    ) -> AsyncIterator[ChatCompletionChunk]:
        payload = openai_to_anthropic(request)
        payload.stream = True
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        try:
            async with http_client.stream(
                "POST", self._url(upstream, "/v1/messages"),
                headers=_headers(upstream.api_key),
                json=payload.model_dump(exclude_none=True),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    etype = event.get("type")
                    if etype == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        yield ChatCompletionChunk(
                            id=chunk_id, created=created, model=request.model,
                            choices=[StreamChoice(index=0, delta=DeltaMessage(content=text))],
                        )
                    elif etype == "message_delta":
                        stop_reason = event.get("delta", {}).get("stop_reason")
                        mapped = STOP_REASON_MAP.get(stop_reason or "end_turn")
                        if mapped is None:
                            logger.debug("unknown_stop_reason", reason=stop_reason)
                            mapped = "stop"
                        yield ChatCompletionChunk(
                            id=chunk_id, created=created, model=request.model,
                            choices=[StreamChoice(
                                index=0, delta=DeltaMessage(),
                                finish_reason=mapped,
                            )],
                        )
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            if isinstance(e, json.JSONDecodeError):
                yield ChatCompletionChunk(
                    id="error",
                    object="chat.completion.chunk",
                    created=0,
                    model=request.model,
                    choices=[StreamChoice(
                        index=0,
                        delta=DeltaMessage(content=json.dumps({"code": "proxy_error", "message": str(e)})),
                        finish_reason="error",
                    )],
                )
                return
            self._raise_for_http_error(e, upstream)
