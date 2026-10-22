"""Editor chat refuses disabled, unavailable or over-budget turns before persisting anything."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.editor.prompt_budget import apply_chat_budget
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatMessage,
    ChatStreamProviderProtocol,
    EditorChatCommand,
    EditorChatDoneDisabledData,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.application_fixtures import FakeTokenCounter, FakeTokenCounterResolver
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
async def test_editor_chat_returns_done_disabled_when_disabled() -> None:
    settings = Settings(LLM_CHAT_ENABLED=False)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

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
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=uuid4(),
                message="Hej",
            ),
        )
    ]

    assert len(events) == 1
    assert events[0].event == "done"
    assert isinstance(events[0], EditorChatDoneEvent)
    assert isinstance(events[0].data, EditorChatDoneDisabledData)
    provider.stream_chat.assert_not_called()
    sessions.get.assert_not_called()
    turns.create_turn.assert_not_called()
    messages.create_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_returns_done_disabled_when_system_prompt_unavailable() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    def system_prompt_loader(template_id: str) -> str:
        del template_id
        raise OSError("missing system prompt")

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
        system_prompt_loader=system_prompt_loader,
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=uuid4(),
                message="Hej",
            ),
        )
    ]

    assert len(events) == 1
    assert events[0].event == "done"
    assert isinstance(events[0], EditorChatDoneEvent)
    assert isinstance(events[0].data, EditorChatDoneDisabledData)
    provider.stream_chat.assert_not_called()
    sessions.get.assert_not_called()
    turns.create_turn.assert_not_called()
    messages.create_message.assert_not_called()


@pytest.mark.unit
def test_apply_chat_budget_drops_oldest_turns_and_never_truncates_system_prompt() -> None:
    system_prompt = "S" * 4
    messages = [
        ChatMessage(role="user", content="A" * 8),
        ChatMessage(role="assistant", content="B" * 8),
        ChatMessage(role="user", content="C" * 8),
    ]

    system_prompt_trimmed, kept = apply_chat_budget(
        system_prompt=system_prompt,
        messages=messages,
        context_window_tokens=5,
        max_output_tokens=0,
        safety_margin_tokens=0,
        system_prompt_max_tokens=1,
        token_counter=FakeTokenCounter(),
    )

    assert system_prompt_trimmed == system_prompt
    assert len(kept) == 1
    assert kept[0].role == "user"
    assert kept[0].content == "C" * 8


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_raises_validation_error_when_message_too_long() -> None:
    settings = Settings(
        LLM_CHAT_ENABLED=True,
        HULEEDU_INTERNAL_API_KEY="test-door-key",
        LLM_CHAT_CONTEXT_WINDOW_TOKENS=5,
        LLM_CHAT_MAX_TOKENS=0,
        LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS=0,
    )
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock()
    turns.cancel_pending_turn = AsyncMock()
    turns.create_turn = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock()
    messages.create_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

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
        system_prompt_loader=lambda _template_id: "S" * 4,
        token_counters=FakeTokenCounterResolver(),
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    with pytest.raises(DomainError) as exc_info:
        async for _event in handler.stream(
            actor=actor,
            command=EditorChatCommand(
                tool_id=uuid4(),
                message="X" * 17,
            ),
        ):
            pass

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "För långt meddelande" in exc_info.value.message
    sessions.get.assert_not_called()
    turns.create_turn.assert_not_called()
    messages.create_message.assert_not_called()
    provider.stream_chat.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_leaves_role_admission_to_the_web_gate() -> None:
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
    actor = make_user(role=Role.USER)
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
    provider.stream_chat.assert_called_once()
    turns.create_turn.assert_awaited_once()
