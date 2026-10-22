from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, ai_limit_note
from skriptoteket.protocols.llm import (
    EditorChatCommand,
    EditorChatDeltaEvent,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatStreamEvent,
    EditorLlmFailureKind,
    EditorLlmProviderError,
)
from tests.fixtures.editor_chat_handler_harness import ChatHandlerHarness, make_chat_handler_harness
from tests.fixtures.identity_fixtures import make_user


async def _collect(
    harness: ChatHandlerHarness, *, user_id: UUID, tool_id: UUID
) -> list[EditorChatStreamEvent]:
    return [
        event
        async for event in harness.handler.stream(
            actor=make_user(role=Role.ADMIN, user_id=user_id),
            command=EditorChatCommand(tool_id=tool_id, message="Hej"),
        )
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_chat_turn_streams_with_a_door_caller_for_the_actor() -> None:
    user_id = uuid4()
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        yield " "
        yield "världen"

    harness.provider.stream_chat.return_value = stream()

    events = await _collect(harness, user_id=user_id, tool_id=tool_id)

    harness.provider.stream_chat.assert_called_once()
    caller = harness.provider.stream_chat.call_args.kwargs["caller"]
    assert caller.user_id == user_id
    assert caller.exempt is True
    assert [event.event for event in events] == ["meta", "delta", "delta", "delta", "done"]
    assert [e.data.text for e in events if isinstance(e, EditorChatDeltaEvent)] == [
        "Hej",
        " ",
        "världen",
    ]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "stop"
    assert harness.guard.held == set()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("limit", list(AiDailyLimit))
async def test_door_limit_on_first_iteration_raises_before_any_event_and_frees_the_turn(
    limit: AiDailyLimit,
) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)

    async def refused() -> AsyncIterator[str]:
        raise AiDailyLimitReached(limit=limit)
        yield ""

    async def answered() -> AsyncIterator[str]:
        yield "Svar"

    harness.provider.stream_chat.side_effect = [refused(), answered()]
    stream = harness.handler.stream(
        actor=make_user(role=Role.ADMIN, user_id=user_id),
        command=EditorChatCommand(tool_id=tool_id, message="Hej"),
    )

    with pytest.raises(DomainError) as exc_info:
        await anext(stream)

    assert exc_info.value.code == ErrorCode.AI_DAILY_LIMIT_REACHED
    assert exc_info.value.message == ai_limit_note(limit)
    assert exc_info.value.details == {"limit": limit.value}
    assert harness.guard.held == set()
    harness.turns.update_status.assert_awaited_once()
    status_call = harness.turns.update_status.call_args.kwargs
    assert status_call["turn_id"] == harness.turn_id
    assert status_call["status"] == "failed"
    assert status_call["failure_outcome"] == "daily_limit"

    events = await _collect(harness, user_id=user_id, tool_id=tool_id)
    assert [event.event for event in events] == ["meta", "delta", "done"]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "outcome"),
    [
        ("timeout", "timeout"),
        ("context_window_exceeded", "over_budget"),
        ("http_status", "error"),
        ("request_failed", "error"),
        ("invalid_response", "error"),
    ],
)
async def test_provider_error_after_a_delta_ends_the_turn_with_done_error(
    kind: EditorLlmFailureKind, outcome: str
) -> None:
    user_id = uuid4()
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)

    async def stream() -> AsyncIterator[str]:
        yield "Del"
        raise EditorLlmProviderError(kind=kind, status_code=502)

    harness.provider.stream_chat.return_value = stream()

    events = await _collect(harness, user_id=user_id, tool_id=tool_id)

    assert [event.event for event in events] == ["meta", "delta", "done"]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "error"
    status_call = harness.turns.update_status.call_args.kwargs
    assert status_call["status"] == "failed"
    assert status_call["failure_outcome"] == outcome
    assert harness.guard.held == set()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_provider_error_before_the_first_delta_still_opens_with_meta() -> None:
    user_id = uuid4()
    tool_id = uuid4()
    harness = make_chat_handler_harness(tool_id=tool_id, user_id=user_id)

    async def stream() -> AsyncIterator[str]:
        raise EditorLlmProviderError(kind="request_failed")
        yield ""

    harness.provider.stream_chat.return_value = stream()

    events = await _collect(harness, user_id=user_id, tool_id=tool_id)

    assert [event.event for event in events] == ["meta", "done"]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "error"
