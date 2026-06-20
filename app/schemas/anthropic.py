import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    ChoiceMessage,
    UsageInfo,
    ChatCompletionChunk,
    StreamChoice,
    DeltaMessage,
)

STOP_REASON_MAP = {
    "end_turn": "stop",
    "max_tokens": "length",
    "stop_sequence": "stop",
}


class AnthropicMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class AnthropicRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    system: str | None = None
    messages: list[AnthropicMessage]
    max_tokens: int = 4096
    temperature: float | None = None
    top_p: float | None = None
    stream: bool = False
    stop_sequences: list[str] | None = None


class AnthropicContentBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    text: str | None = None


class AnthropicUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_tokens: int = 0
    output_tokens: int = 0


class AnthropicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str = "message"
    role: str = "assistant"
    content: list[AnthropicContentBlock]
    model: str
    stop_reason: str | None = None
    usage: AnthropicUsage


def openai_to_anthropic(req: ChatCompletionRequest) -> AnthropicRequest:
    system: str | None = None
    messages: list[AnthropicMessage] = []
    for msg in req.messages:
        if msg.role == "system":
            system = msg.content
        else:
            messages.append(AnthropicMessage(role=msg.role, content=msg.content))
    return AnthropicRequest(
        model=req.model,
        system=system,
        messages=messages,
        max_tokens=req.max_tokens or 4096,
        temperature=req.temperature,
        top_p=req.top_p,
        stream=req.stream,
        stop_sequences=[req.stop] if isinstance(req.stop, str) else req.stop,
    )


def anthropic_to_openai(resp: AnthropicResponse, model: str) -> ChatCompletionResponse:
    text = next((b.text for b in resp.content if b.type == "text" and b.text), "")
    return ChatCompletionResponse(
        id=f"chatcmpl-{resp.id}",
        created=int(time.time()),
        model=model,
        choices=[
            Choice(
                index=0,
                message=ChoiceMessage(role="assistant", content=text),
                finish_reason=STOP_REASON_MAP.get(resp.stop_reason or "end_turn", "stop"),
            )
        ],
        usage=UsageInfo(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        ),
    )
