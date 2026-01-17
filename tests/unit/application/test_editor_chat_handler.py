from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import httpx
import pytest

from skriptoteket.application.editor.chat_handler import EditorChatHandler
from skriptoteket.application.editor.chat_prompt_builder import SettingsBasedEditorChatPromptBuilder
from skriptoteket.application.editor.chat_stream_orchestrator import EditorChatStreamOrchestrator
from skriptoteket.application.editor.chat_turn_preparer import EditorChatTurnPreparer
from skriptoteket.application.editor.prompt_budget import apply_chat_budget
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
    ChatMessage,
    ChatStreamProviderProtocol,
    EditorChatCommand,
    EditorChatDeltaEvent,
    EditorChatDoneDisabledData,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatMetaEvent,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.application_fixtures import FakeTokenCounter, FakeTokenCounterResolver
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
    token_counters: FakeTokenCounterResolver,
    system_prompt_loader=None,
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


def _make_turn(
    *,
    turn_id: UUID,
    tool_session_id: UUID,
    status: str,
    created_at: datetime,
) -> ToolSessionTurn:
    return ToolSessionTurn(
        id=turn_id,
        tool_session_id=tool_session_id,
        status=status,  # type: ignore[arg-type]
        failure_outcome=None,
        provider=None,
        correlation_id=None,
        sequence=1,
        created_at=created_at,
        updated_at=created_at,
    )


def _dummy_message(*, tool_session_id: UUID, turn_id: UUID, message_id: UUID) -> ToolSessionMessage:
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

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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
    settings = Settings(LLM_CHAT_ENABLED=True)
    provider = MagicMock(spec=ChatStreamProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    def system_prompt_loader(template_id: str) -> str:
        del template_id
        raise OSError("missing system prompt")

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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
@pytest.mark.asyncio
async def test_editor_chat_streams_meta_delta_done_and_persists_turn() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
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
    actor = make_user(role=Role.CONTRIBUTOR)
    session = _make_tool_session(
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

    turns.create_turn.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="complete",
        created_at=session.created_at,
    )

    messages.create_message.return_value = _dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        yield " världen"

    provider.stream_chat.return_value = stream()

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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

    assert [event.event for event in events] == ["meta", "delta", "delta", "done"]
    assert isinstance(events[0], EditorChatMetaEvent)
    assert events[0].data.turn_id == turn_id
    assert events[0].data.assistant_message_id == assistant_message_id

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

    assert turns.create_turn.call_count == 1
    assert messages.create_message.call_count == 2

    user_call = messages.create_message.call_args_list[0].kwargs
    assert user_call["turn_id"] == turn_id
    assert user_call["message_id"] == user_message_id
    assert user_call["role"] == "user"
    assert user_call["content"] == "Hej"

    assistant_call = messages.create_message.call_args_list[1].kwargs
    assert assistant_call["turn_id"] == turn_id
    assert assistant_call["message_id"] == assistant_message_id
    assert assistant_call["role"] == "assistant"
    assert assistant_call["content"] == ""
    assert assistant_call["meta"]["in_reply_to"] == str(user_message_id)

    messages.update_message_content_if_pending_turn.assert_called()
    assert (
        messages.update_message_content_if_pending_turn.call_args.kwargs["content"] == "Hej världen"
    )

    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["turn_id"] == turn_id
    assert turns.update_status.call_args.kwargs["status"] == "complete"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_emits_done_error_on_timeout_and_marks_turn_failed() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
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
    actor = make_user(role=Role.CONTRIBUTOR)
    session = _make_tool_session(
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

    turns.create_turn.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="failed",
        created_at=session.created_at,
    )

    messages.create_message.return_value = _dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    provider.stream_chat.side_effect = httpx.ReadTimeout(
        "timeout",
        request=httpx.Request("POST", "http://test"),
    )

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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

    assert [event.event for event in events] == ["meta", "done"]
    assert isinstance(events[-1], EditorChatDoneEvent)
    assert isinstance(events[-1].data, EditorChatDoneEnabledData)
    assert events[-1].data.reason == "error"

    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["status"] == "failed"
    assert turns.update_status.call_args.kwargs["failure_outcome"] == "timeout"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_chat_persists_partial_assistant_message_on_timeout_after_deltas() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
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
    actor = make_user(role=Role.CONTRIBUTOR)
    session = _make_tool_session(
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

    turns.create_turn.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="pending",
        created_at=session.created_at,
    )
    turns.update_status.return_value = _make_turn(
        turn_id=turn_id,
        tool_session_id=session.id,
        status="failed",
        created_at=session.created_at,
    )

    messages.create_message.return_value = _dummy_message(
        tool_session_id=session.id, turn_id=turn_id, message_id=user_message_id
    )

    async def stream() -> AsyncIterator[str]:
        yield "Hej"
        raise httpx.ReadTimeout("timeout", request=httpx.Request("POST", "http://test"))

    provider.stream_chat.return_value = stream()

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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
    assert events[-1].data.reason == "error"

    messages.update_message_content_if_pending_turn.assert_called()
    assert messages.update_message_content_if_pending_turn.call_args.kwargs["content"] == "Hej"
    turns.update_status.assert_called_once()
    assert turns.update_status.call_args.kwargs["failure_outcome"] == "timeout"


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

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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
async def test_editor_chat_drops_expired_thread_history() -> None:
    settings = Settings(LLM_CHAT_ENABLED=True)
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

    expired_session = _make_tool_session(
        tool_id=tool_id,
        user_id=actor.id,
        state={"base_version_id": str(uuid4())},
        state_rev=5,
        updated_at=now - timedelta(days=31),
    )
    sessions.get.return_value = expired_session
    sessions.clear_state.return_value = expired_session
    turns.list_tail.return_value = [
        _make_turn(
            turn_id=uuid4(),
            tool_session_id=expired_session.id,
            status="complete",
            created_at=now - timedelta(days=31),
        )
    ]

    async def stream() -> AsyncIterator[str]:
        yield "Hej"

    provider.stream_chat.return_value = stream()

    providers = MagicMock()
    providers.primary = provider
    providers.fallback = None
    providers.fallback_is_remote = False

    turn_id = uuid4()
    user_message_id = uuid4()
    assistant_message_id = uuid4()
    id_generator.new_uuid.side_effect = [turn_id, user_message_id, assistant_message_id]

    handler = _make_handler(
        settings=settings,
        providers=providers,
        guard=DummyChatGuard(),
        failover=DummyFailover(),
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
