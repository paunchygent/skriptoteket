import json
from collections.abc import AsyncIterator
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
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
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token
from skriptoteket.web.editor_support import require_tool_access

from .models import EditorChatHistoryMessage, EditorChatHistoryResponse, EditorChatRequest

router = APIRouter()


def _encode_sse_event(event: EditorChatStreamEvent) -> bytes:
    payload = json.dumps(
        event.data.model_dump(mode="json"),
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

    command = EditorChatCommand(
        tool_id=tool_id,
        message=payload.message,
        base_version_id=payload.base_version_id,
        allow_remote_fallback=payload.allow_remote_fallback,
        active_file=payload.active_file,
        virtual_files=payload.virtual_files.as_map() if payload.virtual_files is not None else None,
    )
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


@router.get("/tools/{tool_id}/chat", response_model=EditorChatHistoryResponse)
@inject
async def get_editor_chat_history(
    tool_id: UUID,
    handler: FromDishka[EditorChatHistoryHandlerProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    user: User = Depends(require_contributor_api),
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
