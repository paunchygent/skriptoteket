"""A real EditorChatHandler over mocked repositories, for chat stream proofs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import chain
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_prompt_builder import SettingsBasedEditorChatPromptBuilder
from skriptoteket.application.editor.chat_stream_orchestrator import EditorChatStreamOrchestrator
from skriptoteket.application.editor.chat_turn_preparer import EditorChatTurnPreparer
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
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

_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


class SlotChatGuard(ChatInFlightGuardProtocol):
    """In-flight guard that keeps the held (user, tool) slots like the real one."""

    def __init__(self) -> None:
        self.held: set[tuple[UUID, UUID]] = set()

    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        if (user_id, tool_id) in self.held:
            return False
        self.held.add((user_id, tool_id))
        return True

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        self.held.discard((user_id, tool_id))


class _ChatBudgetResolver(ChatBudgetResolverProtocol):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def resolve_chat_budget(self) -> ChatBudget:
        return ChatBudget(
            context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
        )


class _NoopUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> "_NoopUow":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@dataclass(frozen=True, slots=True)
class ChatHandlerHarness:
    handler: EditorChatHandler
    provider: MagicMock
    guard: SlotChatGuard
    turns: MagicMock
    messages: MagicMock
    turn_id: UUID
    assistant_message_id: UUID


def make_chat_handler_harness(*, tool_id: UUID, user_id: UUID) -> ChatHandlerHarness:
    """Build a handler whose one allowed turn persists into mocked repositories."""

    settings = Settings(LLM_CHAT_ENABLED=True, HULEEDU_INTERNAL_API_KEY="test-door-key")
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    guard = SlotChatGuard()

    session = ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
        state={},
        state_rev=0,
        created_at=_NOW,
        updated_at=_NOW,
    )
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock(return_value=session)

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    turn = ToolSessionTurn(
        id=turn_id,
        tool_session_id=session.id,
        status="pending",
        failure_outcome=None,
        provider=None,
        correlation_id=None,
        sequence=1,
        created_at=_NOW,
        updated_at=_NOW,
    )
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(return_value=None)
    turns.create_turn = AsyncMock(return_value=turn)
    turns.update_status = AsyncMock(return_value=turn)

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock(
        return_value=ToolSessionMessage(
            id=uuid4(),
            tool_session_id=session.id,
            turn_id=turn_id,
            message_id=user_message_id,
            role="user",
            content="",
            meta=None,
            sequence=1,
            created_at=_NOW,
        )
    )
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    id_generator = MagicMock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = chain(
        [turn_id, user_message_id, assistant_message_id], iter(uuid4, None)
    )

    uow = _NoopUow()
    turn_preparer = EditorChatTurnPreparer(
        settings=settings,
        prompt_builder=SettingsBasedEditorChatPromptBuilder(settings=settings),
        uow=uow,
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=MagicMock(spec=ClockProtocol),
        id_generator=id_generator,
    )
    stream_orchestrator = EditorChatStreamOrchestrator(
        settings=settings,
        capture_store=MagicMock(spec=LlmCaptureStoreProtocol),
        provider=provider,
        uow=uow,
        turns=turns,
        messages=messages,
    )
    handler = EditorChatHandler(
        settings=settings,
        guard=guard,
        budget_resolver=_ChatBudgetResolver(settings=settings),
        turn_preparer=turn_preparer,
        stream_orchestrator=stream_orchestrator,
        token_counters=FakeTokenCounterResolver(),
        system_prompt_loader=lambda _template_id: "system prompt",
    )
    return ChatHandlerHarness(
        handler=handler,
        provider=provider,
        guard=guard,
        turns=turns,
        messages=messages,
        turn_id=turn_id,
        assistant_message_id=assistant_message_id,
    )
