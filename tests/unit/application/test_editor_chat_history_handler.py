from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.editor.chat_history_handler import EditorChatHistoryHandler
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.llm import EditorChatHistoryQuery
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


class DummyUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> "DummyUow":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


def _make_tool_session(
    *,
    tool_id: UUID,
    user_id: UUID,
    state: dict[str, object],
    updated_at: datetime,
) -> ToolSession:
    return ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
        state=state,
        state_rev=0,
        created_at=updated_at,
        updated_at=updated_at,
    )


def _make_turn(*, tool_session_id: UUID, created_at: datetime) -> ToolSessionTurn:
    return ToolSessionTurn(
        id=uuid4(),
        tool_session_id=tool_session_id,
        status="complete",
        failure_outcome=None,
        provider=None,
        correlation_id=None,
        sequence=1,
        created_at=created_at,
        updated_at=created_at,
    )


def _make_message(
    *,
    tool_session_id: UUID,
    turn_id: UUID,
    role: str,
    content: str,
    created_at: datetime,
    meta: dict[str, object] | None = None,
) -> ToolSessionMessage:
    return ToolSessionMessage(
        id=uuid4(),
        tool_session_id=tool_session_id,
        turn_id=turn_id,
        message_id=uuid4(),
        role=role,  # type: ignore[arg-type]
        content=content,
        meta=meta,
        sequence=1,
        created_at=created_at,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_history_returns_tail_and_base_version_id() -> None:
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock = FixedClock(now=now)
    tool_id = uuid4()
    base_version_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)

    session = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={"base_version_id": str(base_version_id)},
        updated_at=now,
    )

    turn = _make_turn(tool_session_id=session.id, created_at=now)
    message = _make_message(
        tool_session_id=session.id,
        turn_id=turn.id,
        role="user",
        content="Hej",
        created_at=now,
    )

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[turn])

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[message])

    handler = EditorChatHistoryHandler(
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=60),
    )

    assert result.base_version_id == base_version_id
    assert result.turns == [turn]
    assert result.messages == [message]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_history_ttl_expiry_clears_state() -> None:
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    clock = FixedClock(now=now)
    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)

    session = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={"base_version_id": str(uuid4())},
        updated_at=now - timedelta(days=31),
    )

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)
    sessions.clear_state = AsyncMock(return_value=session)

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(
        return_value=[_make_turn(tool_session_id=session.id, created_at=now - timedelta(days=31))]
    )
    turns.delete_all = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])

    handler = EditorChatHistoryHandler(
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=60),
    )

    assert result.turns == []
    assert result.messages == []
    assert result.base_version_id is None
    turns.delete_all.assert_called_once_with(tool_session_id=session.id)
    sessions.clear_state.assert_called_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="editor_chat",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_history_filters_hidden_context_messages() -> None:
    now = datetime(2025, 1, 2, tzinfo=timezone.utc)
    clock = FixedClock(now=now)
    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)

    session = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={},
        updated_at=now,
    )
    turn = _make_turn(tool_session_id=session.id, created_at=now)

    visible_user = _make_message(
        tool_session_id=session.id,
        turn_id=turn.id,
        role="user",
        content="Hej",
        created_at=now,
    )
    hidden_context = _make_message(
        tool_session_id=session.id,
        turn_id=turn.id,
        role="assistant",
        content="ignored",
        created_at=now,
        meta={"hidden": True, "kind": "virtual_file_context"},
    )
    hidden_by_kind_only = _make_message(
        tool_session_id=session.id,
        turn_id=turn.id,
        role="assistant",
        content="ignored",
        created_at=now,
        meta={"kind": "virtual_file_context"},
    )
    visible_assistant = _make_message(
        tool_session_id=session.id,
        turn_id=turn.id,
        role="assistant",
        content="Svar",
        created_at=now,
    )

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[turn])

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(
        return_value=[visible_user, hidden_context, hidden_by_kind_only, visible_assistant]
    )

    handler = EditorChatHistoryHandler(
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=60),
    )

    assert result.messages == [visible_user, visible_assistant]
