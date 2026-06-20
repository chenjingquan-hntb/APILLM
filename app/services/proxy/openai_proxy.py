import json
from typing import AsyncIterator
from pydantic import ValidationError
import httpx
from app.db.models import Upstream
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse, ChatCompletionChunk, StreamChoice, DeltaMessage
from app.services.proxy.base import BaseProxyHandler, http_client, auth_header


class OpenAIProxyHandler(BaseProxyHandler):
    async def forward(self, request: ChatCompletionRequest, upstream: Upstream) -> ChatCompletionResponse:
        try:
            resp = await http_client.post(
                self._url(upstream, "/v1/chat/completions"),
                headers=auth_header(upstream.api_key),
                json=request.model_dump(exclude_none=True),
            )
            resp.raise_for_status()
            return ChatCompletionResponse.model_validate(resp.json())
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValidationError) as e:
            self._raise_for_http_error(e, upstream)

    async def forward_stream(
        self, request: ChatCompletionRequest, upstream: Upstream
    ) -> AsyncIterator[ChatCompletionChunk]:
        payload = request.model_dump(exclude_none=True)
        payload["stream"] = True
        try:
            async with http_client.stream(
                "POST", self._url(upstream, "/v1/chat/completions"),
                headers=auth_header(upstream.api_key),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        return
                    yield ChatCompletionChunk.model_validate_json(data)
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValidationError) as e:
            if not isinstance(e, (httpx.HTTPStatusError, httpx.RequestError)):
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
