from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_prompt_builder import SettingsBasedEditorChatPromptBuilder
from skriptoteket.application.editor.chat_stream_orchestrator import EditorChatStreamOrchestrator
from skriptoteket.application.editor.chat_turn_preparer import EditorChatTurnPreparer
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_messages import ToolSessionMessage
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatBudget,
    ChatBudgetResolverProtocol,
    ChatFailoverDecision,
    ChatFailoverProvider,
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatStreamProviderProtocol,
    EditorChatCommand,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
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


class DummyChatBudgetResolver(ChatBudgetResolverProtocol):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def resolve_chat_budget(self, *, provider: ChatFailoverProvider) -> ChatBudget:
        del provider
        return ChatBudget(
            context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
        )


def _make_handler(
    *,
    settings: Settings,
    providers,
    guard: ChatInFlightGuardProtocol,
    failover: ChatFailoverRouterProtocol,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    system_prompt_loader=None,
    token_counters: FakeTokenCounterResolver,
) -> EditorChatHandler:
    prompt_builder = SettingsBasedEditorChatPromptBuilder(settings=settings)
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
        providers=providers,
        failover=failover,
        uow=uow,
        turns=turns,
        messages=messages,
    )
    return EditorChatHandler(
        settings=settings,
        providers=providers,
        guard=guard,
        failover=failover,
        budget_resolver=DummyChatBudgetResolver(settings=settings),
        turn_preparer=turn_preparer,
        stream_orchestrator=stream_orchestrator,
        token_counters=token_counters,
        system_prompt_loader=system_prompt_loader,
    )


def _make_session(*, tool_id: UUID, user_id: UUID) -> ToolSession:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
        state={},
        state_rev=0,
        created_at=now,
        updated_at=now,
    )


def _make_turn(*, tool_session_id: UUID, status: str) -> ToolSessionTurn:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSessionTurn(
        id=uuid4(),
        tool_session_id=tool_session_id,
        status=status,  # type: ignore[arg-type]
        failure_outcome=None,
        provider=None,
        correlation_id=None,
        sequence=1,
        created_at=now,
        updated_at=now,
    )


def _dummy_message(*, tool_session_id: UUID, turn_id: UUID) -> ToolSessionMessage:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSessionMessage(
        id=uuid4(),
        tool_session_id=tool_session_id,
        turn_id=turn_id,
        message_id=uuid4(),
        role="user",
        content="",
        meta=None,
        sequence=1,
        created_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_guard_rejects_concurrent_request() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=BlockChatGuard(),
        failover=DummyFailover(),
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _template_id: "prompt",
        token_counters=FakeTokenCounterResolver(),
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
    turns.create_turn.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_cancels_pending_turn_when_starting_new_request() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)

    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(
        return_value=_make_turn(tool_session_id=uuid4(), status="cancelled")
    )
    turns.create_turn = AsyncMock(
        return_value=_make_turn(tool_session_id=uuid4(), status="pending")
    )
    turns.update_status = AsyncMock(
        return_value=_make_turn(tool_session_id=uuid4(), status="complete")
    )

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock()
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    tool_id = uuid4()
    actor = make_user(role=Role.CONTRIBUTOR)
    session = _make_session(tool_id=tool_id, user_id=actor.id)
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

    messages.create_message.return_value = _dummy_message(
        tool_session_id=session.id, turn_id=turn_id
    )

    async def stream() -> AsyncIterator[str]:
        yield "Svar"

    provider.stream_chat.return_value = stream()

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=AllowChatGuard(),
        failover=DummyFailover(),
        uow=DummyUow(),
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _template_id: "prompt",
        token_counters=FakeTokenCounterResolver(),
    )

    events = [
        event
        async for event in handler.stream(
            actor=actor,
            command=EditorChatCommand(tool_id=tool_id, message="Hej"),
        )
    ]

    assert [event.event for event in events] == ["meta", "delta", "done"]
    turns.cancel_pending_turn.assert_called_once()
    assert (
        turns.cancel_pending_turn.call_args.kwargs["failure_outcome"] == "abandoned_by_new_request"
    )
