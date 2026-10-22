"""Editor chat API routes.

Purpose:
    Stream and manage assistant chat turns for the tool editor.

Relationships:
    - Uses editor application handlers for chat orchestration and history.
    - A door daily-limit refusal reaches the client as HTTP 429 before the SSE
      response opens, because the first handler event is awaited first.
"""

import json
from collections.abc import AsyncGenerator
from contextlib import aclosing
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.llm import (
    EditorChatClearCommand,
    EditorChatClearHandlerProtocol,
    EditorChatCommand,
    EditorChatHandlerProtocol,
    EditorChatHistoryHandlerProtocol,
    EditorChatHistoryQuery,
    EditorChatStreamEvent,
)
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_contributor_api,
)
from skriptoteket.web.closing_stream import (
    ClosingStreamingResponse,
    anext_unaffected_by_scope_cancel,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.editor_support import require_tool_access

from .models.requests import EditorChatRequest
from .models.responses import EditorChatHistoryMessage, EditorChatHistoryResponse

router = APIRouter()


def _encode_sse_event(event: EditorChatStreamEvent) -> bytes:
    payload = json.dumps(
        event.data.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event.event}\ndata: {payload}\n\n".encode("utf-8")


async def _sse_frames(
    *,
    first_event: EditorChatStreamEvent,
    events: AsyncGenerator[EditorChatStreamEvent, None],
) -> AsyncGenerator[bytes, None]:
    """Encode the events; this generator owns the close of ``events``."""

    async with aclosing(events):
        yield _encode_sse_event(first_event)
        while True:
            try:
                event = await anext_unaffected_by_scope_cancel(events)
            except StopAsyncIteration:
                return
            yield _encode_sse_event(event)


@router.post("/tools/{tool_id}/chat", response_class=StreamingResponse)
async def stream_editor_chat(
    tool_id: UUID,
    payload: EditorChatRequest,
    handler: FromDishka[EditorChatHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_app_contributor_api),
) -> Response:
    await require_tool_access(actor=user, tool_id=tool_id, maintainers=maintainers)
    command = EditorChatCommand(
        tool_id=tool_id,
        message=payload.message,
        base_version_id=payload.base_version_id,
        active_file=payload.active_file,
        virtual_files=payload.virtual_files.as_map() if payload.virtual_files is not None else None,
    )
    stream_iter = handler.stream(actor=user, command=command)
    first_event = await anext(stream_iter)

    return ClosingStreamingResponse(
        _sse_frames(first_event=first_event, events=stream_iter),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
        },
    )


@router.get("/tools/{tool_id}/chat", response_model=EditorChatHistoryResponse)
async def get_editor_chat_history(
    tool_id: UUID,
    handler: FromDishka[EditorChatHistoryHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_app_contributor_api),
    limit: int = Query(60, ge=1, le=200),
) -> EditorChatHistoryResponse:
    await require_tool_access(actor=user, tool_id=tool_id, maintainers=maintainers)
    result = await handler.handle(
        actor=user,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=limit),
    )
    turn_by_id = {turn.id: turn for turn in result.turns}
    messages: list[EditorChatHistoryMessage] = []
    for message in result.messages:
        turn = turn_by_id.get(message.turn_id)
        messages.append(
            EditorChatHistoryMessage(
                message_id=message.message_id,
                turn_id=message.turn_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                status=turn.status if turn is not None else "failed",
                correlation_id=turn.correlation_id if turn is not None else None,
                failure_outcome=turn.failure_outcome if turn is not None else None,
            )
        )
    return EditorChatHistoryResponse(messages=messages, base_version_id=result.base_version_id)


@router.delete("/tools/{tool_id}/chat", status_code=204)
async def clear_editor_chat(
    tool_id: UUID,
    handler: FromDishka[EditorChatClearHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_app_contributor_api),
) -> Response:
    await require_tool_access(actor=user, tool_id=tool_id, maintainers=maintainers)
    await handler.handle(
        actor=user,
        command=EditorChatClearCommand(tool_id=tool_id),
    )
    return Response(status_code=204)
