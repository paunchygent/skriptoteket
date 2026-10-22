"""Editor chat streams persist the turn, partial text and failure outcome."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatStreamProviderProtocol,
    EditorChatCommand,
    EditorChatDeltaEvent,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatMetaEvent,
    EditorLlmProviderError,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.editor_chat_handler_support import (
    DummyChatGuard,
    DummyUow,
    make_dummy_message,
    make_handler,
    make_tool_session,
    make_turn,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_streams_meta_delta_done_and_persists_turn() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(return_value=None)
    turns.create_turn = AsyncMock()
    turns.update_status = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock()
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        state_rev=0,
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sessions.get_or_create.return_value = session

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    new_session_id = uuid4()
    id_generator.new_uuid.side_effect = [
        turn_id,
        user_message_id,
        assistant_message_id,
        new_session_id,
    ]

    turns.create_turn.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="complete",
        created_at=session.created_at,
    )

    messages.create_message.return_value = make_dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        yield " världen"

    provider.stream_chat.return_value = stream()

    handler = make_handler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id: "system prompt",
    )

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=tool_id,
                message="Hej",
            ),
        )
    ]

    assert [event.event for event in events] == ["meta", "delta", "delta", "done"]
    assert isinstance(events[0], EditorChatMetaEvent)
    assert events[0].data.turn_id == turn_id
    assert events[0].data.assistant_message_id == assistant_message_id

    deltas: list[str] = []
    for event in events:
        if event.event != "delta":
            continue
        assert isinstance(event, EditorChatDeltaEvent)
        deltas.append(event.data.text)
    assert deltas == ["Hej", " världen"]

    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "stop"

    assert turns.create_turn.call_count == 1
    assert messages.create_message.call_count == 2

    user_call = messages.create_message.call_args_list[0].kwargs
    assert user_call["turn_id"] == turn_id
    assert user_call["message_id"] == user_message_id
    assert user_call["role"] == "user"
    assert user_call["content"] == "Hej"

    assistant_call = messages.create_message.call_args_list[1].kwargs
    assert assistant_call["turn_id"] == turn_id
    assert assistant_call["message_id"] == assistant_message_id
    assert assistant_call["role"] == "assistant"
    assert assistant_call["content"] == ""
    assert assistant_call["meta"]["in_reply_to"] == str(user_message_id)

    messages.update_message_content_if_pending_turn.assert_called()
    assert (
        messages.update_message_content_if_pending_turn.call_args.kwargs["content"] == "Hej världen"
    )

    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["turn_id"] == turn_id
    assert turns.update_status.call_args.kwargs["status"] == "complete"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_emits_done_error_on_timeout_and_marks_turn_failed() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(return_value=None)
    turns.create_turn = AsyncMock()
    turns.update_status = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock()
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        state_rev=0,
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sessions.get_or_create.return_value = session

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    new_session_id = uuid4()
    id_generator.new_uuid.side_effect = [
        turn_id,
        user_message_id,
        assistant_message_id,
        new_session_id,
    ]

    turns.create_turn.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="failed",
        created_at=session.created_at,
    )

    messages.create_message.return_value = make_dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    provider.stream_chat.side_effect = EditorLlmProviderError(kind="timeout")

    handler = make_handler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id: "system prompt",
    )

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=tool_id,
                message="Hej",
            ),
        )
    ]

    assert [event.event for event in events] == ["meta", "done"]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "error"

    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["status"] == "failed"
    assert turns.update_status.call_args.kwargs["failure_outcome"] == "timeout"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_persists_partial_assistant_message_on_timeout_after_deltas() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(return_value=None)
    turns.create_turn = AsyncMock()
    turns.update_status = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock()
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        state_rev=0,
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    sessions.get_or_create.return_value = session

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    new_session_id = uuid4()
    id_generator.new_uuid.side_effect = [
        turn_id,
        user_message_id,
        assistant_message_id,
        new_session_id,
    ]

    turns.create_turn.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="failed",
        created_at=session.created_at,
    )

    messages.create_message.return_value = make_dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        raise EditorLlmProviderError(kind="timeout")

    provider.stream_chat.return_value = stream()

    handler = make_handler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id: "system prompt",
    )

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=tool_id,
                message="Hej",
            ),
        )
    ]

    assert [event.event for event in events] == ["meta", "delta", "done"]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "error"

    messages.update_message_content_if_pending_turn.assert_called()
    assert messages.update_message_content_if_pending_turn.call_args.kwargs["content"] == "Hej"
    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["failure_outcome"] == "timeout"
