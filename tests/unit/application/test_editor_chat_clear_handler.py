from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.application.editor.clear_chat_handler import EditorChatClearHandler
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.llm import EditorChatClearCommand
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


def _make_tool_session(*, tool_id, user_id, state) -> ToolSession:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
        state=state,
        state_rev=0,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_editor_chat_noop_when_session_missing() -> None:
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.delete_all = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.delete_all = AsyncMock()

    handler = EditorChatClearHandler(
        uow=DummyUow(), sessions=sessions, turns=turns, messages=messages
    )
    actor = make_user(role=Role.CONTRIBUTOR)

    await handler.handle(actor=actor, command=EditorChatClearCommand(tool_id=uuid4()))

    turns.delete_all.assert_not_called()
    sessions.clear_state.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_editor_chat_deletes_messages_and_clears_state() -> None:
    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id, state={"messages": ["old"]})

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=session)
    sessions.clear_state = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.delete_all = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.delete_all = AsyncMock()

    handler = EditorChatClearHandler(
        uow=DummyUow(), sessions=sessions, turns=turns, messages=messages
    )

    await handler.handle(actor=actor, command=EditorChatClearCommand(tool_id=tool_id))

    turns.delete_all.assert_called_once_with(tool_session_id=session.id)
    sessions.clear_state.assert_called_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="editor_chat",
    )
