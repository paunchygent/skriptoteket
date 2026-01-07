import json
from collections.abc import AsyncIterator
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditorChatClearCommand,
    EditorChatClearHandlerProtocol,
    EditorChatCommand,
    EditorChatHandlerProtocol,
    EditorChatStreamEvent,
)
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token
from skriptoteket.web.editor_support import require_tool_access

from .models import EditorChatRequest

router = APIRouter()


def _encode_sse_event(event: EditorChatStreamEvent) -> bytes:
    payload = json.dumps(
        event.data.model_dump(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event.event}\ndata: {payload}\n\n".encode("utf-8")


@router.post("/tools/{tool_id}/chat", response_class=StreamingResponse)
@inject
async def stream_editor_chat(
    tool_id: UUID,
    payload: EditorChatRequest,
    handler: FromDishka[EditorChatHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> Response:
    await require_tool_access(actor=user, tool_id=tool_id, maintainers=maintainers)

    command = EditorChatCommand(tool_id=tool_id, message=payload.message)
    stream_iter = handler.stream(actor=user, command=command)

    first_event = await anext(stream_iter)

    async def stream() -> AsyncIterator[bytes]:
        yield _encode_sse_event(first_event)

        async for event in stream_iter:
            yield _encode_sse_event(event)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.delete("/tools/{tool_id}/chat", status_code=204)
@inject
async def clear_editor_chat(
    tool_id: UUID,
    handler: FromDishka[EditorChatClearHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> Response:
    await require_tool_access(actor=user, tool_id=tool_id, maintainers=maintainers)

    await handler.handle(
        actor=user,
        command=EditorChatClearCommand(tool_id=tool_id),
    )
    return Response(status_code=204)
