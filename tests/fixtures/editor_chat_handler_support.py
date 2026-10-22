"""Building blocks for editor chat handler tests that arrange their own mocks.

Purpose:
    Share the handler wiring and the session, turn and message builders used by
    the per-behaviour editor chat handler tests, each of which arranges its own
    repository mocks and asserts on them.

Relationships:
    ``tests.fixtures.editor_chat_handler_harness`` offers the ready-made single
    allowed turn; this module wires the same handler over caller-supplied mocks.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_prompt_builder import SettingsBasedEditorChatPromptBuilder
from skriptoteket.application.editor.chat_stream_orchestrator import EditorChatStreamOrchestrator
from skriptoteket.application.editor.chat_turn_preparer import EditorChatTurnPreparer
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import (
    ToolSessionTurn,
    ToolSessionTurnStatus,
)
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatBudget,
    ChatBudgetResolverProtocol,
    ChatInFlightGuardProtocol,
    ChatStreamProviderProtocol,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver


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


class DummyChatBudgetResolver(ChatBudgetResolverProtocol):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def resolve_chat_budget(self) -> ChatBudget:
        return ChatBudget(
            context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
        )


def make_handler(
    *,
    settings: Settings,
    provider: ChatStreamProviderProtocol,
    guard: ChatInFlightGuardProtocol,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    token_counters: FakeTokenCounterResolver,
    system_prompt_loader: Callable[[str], str] | None = None,
) -> EditorChatHandler:
    prompt_builder = SettingsBasedEditorChatPromptBuilder(settings=settings)
    capture_store = MagicMock(spec=LlmCaptureStoreProtocol)
    turn_preparer = EditorChatTurnPreparer(
        settings=settings,
        prompt_builder=prompt_builder,
        uow=uow,
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
    )
    stream_orchestrator = EditorChatStreamOrchestrator(
        settings=settings,
        capture_store=capture_store,
        provider=provider,
        uow=uow,
        turns=turns,
        messages=messages,
    )
    return EditorChatHandler(
        settings=settings,
        guard=guard,
        budget_resolver=DummyChatBudgetResolver(settings=settings),
        turn_preparer=turn_preparer,
        stream_orchestrator=stream_orchestrator,
        token_counters=token_counters,
        system_prompt_loader=system_prompt_loader,
    )


def make_tool_session(
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


def make_turn(
    *,
    turn_id: UUID,
    tool_session_id: UUID,
    status: ToolSessionTurnStatus,
    created_at: datetime,
) -> ToolSessionTurn:
    return ToolSessionTurn(
        id=turn_id,
        tool_session_id=tool_session_id,
        status=status,
        failure_outcome=None,
        provider=None,
        correlation_id=None,
        sequence=1,
        created_at=created_at,
        updated_at=created_at,
    )


def make_dummy_message(
    *, tool_session_id: UUID, turn_id: UUID, message_id: UUID
) -> ToolSessionMessage:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSessionMessage(
        id=uuid4(),
        tool_session_id=tool_session_id,
        turn_id=turn_id,
        message_id=message_id,
        role="user",
        content="",
        meta=None,
        sequence=1,
        created_at=now,
    )
