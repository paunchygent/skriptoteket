from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.editor.chat_history_handler import EditorChatHistoryHandler
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.llm import EditorChatHistoryQuery
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
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

    message = ToolSessionMessage(
        id=uuid4(),
        tool_session_id=session.id,
        message_id=uuid4(),
        role="user",
        content="Hej",
        meta=None,
        sequence=1,
        created_at=now,
    )

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[message])

    handler = EditorChatHistoryHandler(
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=60),
    )

    assert result.base_version_id == base_version_id
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

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(
        return_value=[
            ToolSessionMessage(
                id=uuid4(),
                tool_session_id=session.id,
                message_id=uuid4(),
                role="user",
                content="Gammalt",
                meta=None,
                sequence=1,
                created_at=now - timedelta(days=31),
            )
        ]
    )
    messages.delete_all = AsyncMock()

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)
    sessions.clear_state = AsyncMock(return_value=session)

    handler = EditorChatHistoryHandler(
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
    )

    result = await handler.handle(
        actor=actor,
        query=EditorChatHistoryQuery(tool_id=tool_id, limit=60),
    )

    assert result.messages == []
    assert result.base_version_id is None
    messages.delete_all.assert_called_once_with(tool_session_id=session.id)
    sessions.clear_state.assert_called_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="editor_chat",
    )
