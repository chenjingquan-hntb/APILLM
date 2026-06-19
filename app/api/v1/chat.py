from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.base import get_session
from app.db.models import User
from app.db.repositories.upstream_repo import UpstreamRepository
from app.schemas.openai import ChatCompletionRequest
from app.services.router import select_upstream, get_handler

router = APIRouter(tags=["chat"])


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    upstreams = await UpstreamRepository(session).get_enabled()
    upstream = select_upstream(upstreams)
    handler = get_handler(upstream)

    if request.stream:
        async def _stream():
            async for chunk in handler.forward_stream(request, upstream):
                yield f"data: {chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_stream(), media_type="text/event-stream")

    return await handler.forward(request, upstream)
