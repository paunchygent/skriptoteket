from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.prompt_budget import apply_chat_budget
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatInFlightGuardProtocol,
    ChatMessage,
    ChatStreamProviderProtocol,
    EditorChatCommand,
    EditorChatDeltaEvent,
    EditorChatDoneDisabledData,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


class DummyUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> "DummyUow":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class DummyChatGuard(ChatInFlightGuardProtocol):
    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        return True

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        return None


def _make_tool_session(
    *,
    tool_id: UUID,
    user_id: UUID,
    state: dict[str, object],
    state_rev: int,
    updated_at: datetime,
) -> ToolSession:
    created_at = updated_at
    return ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
        state=state,
        state_rev=state_rev,
        created_at=created_at,
        updated_at=updated_at,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_returns_done_disabled_when_disabled() -> None:
    settings = Settings(LLM_CHAT_ENABLED=False)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    sessions.clear_state = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    messages.append_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_returns_done_disabled_when_system_prompt_unavailable() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    def system_prompt_loader(template_id: str) -> str:
        del template_id
        raise OSError("missing system prompt")

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    messages.append_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_streams_meta_delta_done_and_persists_thread() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    messages.get_by_message_id = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)
    user_message_id = uuid4()
    new_session_id = uuid4()
    assistant_message_id = uuid4()
    id_generator.new_uuid.side_effect = [user_message_id, new_session_id, assistant_message_id]

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        yield " världen"

    user_persisted = {"ok": False}

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)

    session_empty = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        state_rev=0,
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    session_id = session_empty.id

    sessions.get.return_value = None
    sessions.get_or_create.return_value = session_empty
    messages.list_tail.return_value = []

    async def append_message(**kwargs):
        if kwargs.get("role") == "user":
            user_persisted["ok"] = True
        return ToolSessionMessage(
            id=uuid4(),
            tool_session_id=session_id,
            message_id=kwargs.get("message_id"),
            role=kwargs.get("role"),
            content=kwargs.get("content"),
            meta=kwargs.get("meta"),
            sequence=1,
            created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )

    messages.append_message.side_effect = append_message
    messages.get_by_message_id.return_value = ToolSessionMessage(
        id=uuid4(),
        tool_session_id=session_id,
        message_id=user_message_id,
        role="user",
        content="Hej",
        meta=None,
        sequence=1,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    def stream_chat(**_kwargs) -> AsyncIterator[str]:
        assert user_persisted["ok"] is True
        return stream()

    provider.stream_chat.side_effect = stream_chat

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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

    assert messages.append_message.call_count == 2
    first_call = messages.append_message.call_args_list[0].kwargs
    assert first_call["role"] == "user"
    assert first_call["content"] == "Hej"
    assert first_call["message_id"] == user_message_id

    second_call = messages.append_message.call_args_list[1].kwargs
    assert second_call["role"] == "assistant"
    assert second_call["content"] == "Hej världen"
    assert second_call["message_id"] == assistant_message_id
    assert second_call["meta"]["in_reply_to"] == str(user_message_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_emits_done_error_on_timeout_and_persists_user_message() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    messages.get_by_message_id = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)
    user_message_id = uuid4()
    session_id = uuid4()
    id_generator.new_uuid.side_effect = [user_message_id, session_id]

    provider.stream_chat.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session_empty = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        state_rev=0,
        updated_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    sessions.get.return_value = None
    sessions.get_or_create.return_value = session_empty
    messages.list_tail.return_value = []

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    messages.append_message.assert_called_once()
    messages.get_by_message_id.assert_not_called()


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
        LLM_CHAT_CONTEXT_WINDOW_TOKENS=5,
        LLM_CHAT_MAX_TOKENS=0,
        LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS=0,
    )
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _template_id: "S" * 4,
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
    messages.append_message.assert_not_called()
    provider.stream_chat.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_drops_expired_thread_history() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock()
    messages.append_message = AsyncMock()
    messages.delete_all = AsyncMock()
    messages.get_by_message_id = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)
    user_message_id = uuid4()
    session_id = uuid4()
    assistant_message_id = uuid4()
    id_generator.new_uuid.side_effect = [user_message_id, session_id, assistant_message_id]

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    clock.now.return_value = now

    expired_session = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={
            "messages": [
                {"role": "user", "content": "Old"},
                {"role": "assistant", "content": "History"},
            ]
        },
        state_rev=5,
        updated_at=now - timedelta(days=31),
    )
    sessions.get.return_value = expired_session
    sessions.clear_state.return_value = expired_session
    messages.list_tail.return_value = [
        ToolSessionMessage(
            id=uuid4(),
            tool_session_id=expired_session.id,
            message_id=uuid4(),
            role="user",
            content="Old",
            meta=None,
            sequence=1,
            created_at=now - timedelta(days=31),
        )
    ]
    messages.get_by_message_id.return_value = ToolSessionMessage(
        id=uuid4(),
        tool_session_id=expired_session.id,
        message_id=user_message_id,
        role="user",
        content="Hej",
        meta=None,
        sequence=2,
        created_at=now,
    )

    async def stream() -> AsyncIterator[str]:
        yield "Hej"

    provider.stream_chat.return_value = stream()

    handler = EditorChatHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    messages.delete_all.assert_called_once_with(tool_session_id=expired_session.id)
    sessions.clear_state.assert_called_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="editor_chat",
    )
    assert messages.append_message.call_count == 2
    first_call = messages.append_message.call_args_list[0].kwargs
    assert first_call["message_id"] == user_message_id
