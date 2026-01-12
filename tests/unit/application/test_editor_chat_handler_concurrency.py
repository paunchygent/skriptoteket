from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatStreamProviderProtocol,
    EditorChatCommand,
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


class AllowChatGuard(ChatInFlightGuardProtocol):
    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        return True

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        return None


class BlockChatGuard(ChatInFlightGuardProtocol):
    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        return False

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        return None


class DummyFailover(ChatFailoverRouterProtocol):
    async def decide_route(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        allow_remote_fallback: bool,
        fallback_available: bool,
        fallback_is_remote: bool,
    ) -> ChatFailoverDecision:
        return ChatFailoverDecision(provider="primary", reason="primary_default")

    async def acquire_inflight(self, *, provider: str) -> None:
        return None

    async def release_inflight(self, *, provider: str) -> None:
        return None

    async def record_success(self, *, provider: str) -> None:
        return None

    async def record_failure(self, *, provider: str) -> None:
        return None

    async def mark_fallback_used(self, *, user_id: UUID, tool_id: UUID) -> None:
        return None


class InMemoryToolSessionMessages(ToolSessionMessageRepositoryProtocol):
    def __init__(self) -> None:
        self._rows: list[ToolSessionMessage] = []
        self._sequence = 0
        self._now = datetime(2025, 1, 1, tzinfo=timezone.utc)

    async def append_message(
        self,
        *,
        tool_session_id: UUID,
        message_id: UUID,
        role: str,
        content: str,
        meta: dict[str, JsonValue] | None = None,
    ) -> ToolSessionMessage:
        self._sequence += 1
        message = ToolSessionMessage(
            id=uuid4(),
            tool_session_id=tool_session_id,
            message_id=message_id,
            role=role,
            content=content,
            meta=meta,
            sequence=self._sequence,
            created_at=self._now,
        )
        self._rows.append(message)
        return message

    async def list_tail(self, *, tool_session_id: UUID, limit: int) -> list[ToolSessionMessage]:
        rows = [row for row in self._rows if row.tool_session_id == tool_session_id]
        return rows[-limit:]

    async def get_by_message_id(
        self, *, tool_session_id: UUID, message_id: UUID
    ) -> ToolSessionMessage | None:
        for row in self._rows:
            if row.tool_session_id == tool_session_id and row.message_id == message_id:
                return row
        return None

    async def delete_all(self, *, tool_session_id: UUID) -> int:
        before = len(self._rows)
        self._rows = [row for row in self._rows if row.tool_session_id != tool_session_id]
        return before - len(self._rows)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_guard_rejects_concurrent_request() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = EditorChatHandler(
        settings=settings,
        providers=providers,
        guard=BlockChatGuard(),
        failover=DummyFailover(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    with pytest.raises(DomainError) as exc_info:
        async for _event in handler.stream(
            actor=actor,
            command=EditorChatCommand(tool_id=uuid4(), message="Hej"),
        ):
            pass

    assert exc_info.value.code == ErrorCode.CONFLICT
    provider.stream_chat.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_assistant_marks_orphaned_when_user_missing() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.get_by_message_id = AsyncMock(return_value=None)
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)
    assistant_message_id = uuid4()
    id_generator.new_uuid.return_value = assistant_message_id

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = EditorChatHandler(
        settings=settings,
        providers=providers,
        guard=AllowChatGuard(),
        failover=DummyFailover(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
    )

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_session_id = uuid4()
    user_message_id = uuid4()

    await handler._persist_assistant_message(
        tool_id=tool_id,
        actor=actor,
        tool_session_id=tool_session_id,
        expected_user_message_id=user_message_id,
        assistant_message="Svar",
    )

    messages.get_by_message_id.assert_called_once_with(
        tool_session_id=tool_session_id,
        message_id=user_message_id,
    )
    messages.append_message.assert_called_once()
    meta = messages.append_message.call_args.kwargs["meta"]
    assert meta["in_reply_to"] == str(user_message_id)
    assert meta["orphaned"] is True
    assert messages.append_message.call_args.kwargs["message_id"] == assistant_message_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_duplicate_user_messages_persist_distinct_assistant_rows() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    messages = InMemoryToolSessionMessages()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    clock.now.return_value = now

    user_message_id_a = uuid4()
    user_message_id_b = uuid4()
    assistant_message_id_a = uuid4()
    assistant_message_id_b = uuid4()
    id_generator.new_uuid.side_effect = [
        user_message_id_a,
        user_message_id_b,
        assistant_message_id_a,
        assistant_message_id_b,
    ]

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    tool_session_id = uuid4()
    sessions.get = AsyncMock(
        return_value=ToolSession(
            id=tool_session_id,
            tool_id=tool_id,
            user_id=actor.id,
            context="editor_chat",
            state={},
            state_rev=0,
            created_at=now,
            updated_at=now,
        )
    )

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = EditorChatHandler(
        settings=settings,
        providers=providers,
        guard=AllowChatGuard(),
        failover=DummyFailover(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
    )

    _budgeted_a, message_id_a, session_id_a = await handler._persist_user_message(
        tool_id=tool_id,
        actor=actor,
        message="Hej",
        system_prompt="system prompt",
        base_version_id=None,
    )
    _budgeted_b, message_id_b, session_id_b = await handler._persist_user_message(
        tool_id=tool_id,
        actor=actor,
        message="Hej",
        system_prompt="system prompt",
        base_version_id=None,
    )

    assert message_id_a == user_message_id_a
    assert message_id_b == user_message_id_b
    assert session_id_a == tool_session_id
    assert session_id_b == tool_session_id

    await handler._persist_assistant_message(
        tool_id=tool_id,
        actor=actor,
        tool_session_id=tool_session_id,
        expected_user_message_id=message_id_a,
        assistant_message="Svar",
    )
    await handler._persist_assistant_message(
        tool_id=tool_id,
        actor=actor,
        tool_session_id=tool_session_id,
        expected_user_message_id=message_id_b,
        assistant_message="Svar",
    )

    user_rows = [row for row in messages._rows if row.role == "user"]
    assert len(user_rows) == 2
    assert {row.message_id for row in user_rows} == {message_id_a, message_id_b}
    assert all(row.content == "Hej" for row in user_rows)

    assistant_rows = [row for row in messages._rows if row.role == "assistant"]
    assert len(assistant_rows) == 2
    assert {row.message_id for row in assistant_rows} == {
        assistant_message_id_a,
        assistant_message_id_b,
    }
    for row in assistant_rows:
        assert row.meta is not None
    assert {row.meta["in_reply_to"] for row in assistant_rows if row.meta} == {
        str(message_id_a),
        str(message_id_b),
    }
