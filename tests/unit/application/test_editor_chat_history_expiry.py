"""Editor chat drops a thread whose history has expired before starting a new turn."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
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
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.editor_chat_handler_support import (
    DummyChatGuard,
    DummyUow,
    make_handler,
    make_tool_session,
    make_turn,
)
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_drops_expired_thread_history() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock()
    sessions.get_or_create = AsyncMock()
    sessions.clear_state = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock()
    turns.delete_all = AsyncMock()
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
    now = datetime(2025, 2, 1, tzinfo=timezone.utc)
    clock.now.return_value = now

    expired_session = make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={"base_version_id": str(uuid4())},
        state_rev=5,
        updated_at=now - timedelta(days=31),
    )
    sessions.get.return_value = expired_session
    sessions.clear_state.return_value = expired_session
    turns.list_tail.return_value = [
        make_turn(
            turn_id=uuid4(),
            tool_session_id=expired_session.id,
            status="complete",
            created_at=now - timedelta(days=31),
        )
    ]

    async def stream() -> AsyncIterator[str]:
        yield "Hej"

    provider.stream_chat.return_value = stream()

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    id_generator.new_uuid.side_effect = [turn_id, user_message_id, assistant_message_id]

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
        system_prompt_loader=lambda _template_id: "system prompt",
        token_counters=FakeTokenCounterResolver(),
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
    turns.delete_all.assert_called_once_with(tool_session_id=expired_session.id)
    sessions.clear_state.assert_called_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        context="editor_chat",
    )
