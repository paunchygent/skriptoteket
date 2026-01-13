from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from structlog.contextvars import bind_contextvars, clear_contextvars

from skriptoteket.application.editor.edit_ops_handler import EditOpsHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProviderProtocol,
    EditOpsCommand,
    LLMChatOpsResponse,
    VirtualFileId,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver
from tests.fixtures.identity_fixtures import make_user


@contextmanager
def _bound_correlation_id(correlation_id: UUID):
    clear_contextvars()
    bind_contextvars(correlation_id=str(correlation_id))
    try:
        yield
    finally:
        clear_contextvars()


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


class DummyChatOpsBudgetResolver(ChatOpsBudgetResolverProtocol):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve_chat_ops_budget(self, *, provider: str) -> ChatOpsBudget:
        return ChatOpsBudget(
            context_window_tokens=self._settings.LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_CHAT_OPS_MAX_TOKENS,
        )


def _make_tool_session(*, tool_id: UUID, user_id: UUID) -> ToolSession:
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


def _make_turn(
    *, turn_id: UUID, tool_session_id: UUID, correlation_id: UUID | None
) -> ToolSessionTurn:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return ToolSessionTurn(
        id=turn_id,
        tool_session_id=tool_session_id,
        status="pending",
        failure_outcome=None,
        provider=None,
        correlation_id=correlation_id,
        sequence=1,
        created_at=now,
        updated_at=now,
    )


def _virtual_files() -> dict[VirtualFileId, str]:
    return {
        "tool.py": "print('hi')\n",
        "entrypoint.txt": "run_tool\n",
        "settings_schema.json": '{\n  "type": "object"\n}\n',
        "input_schema.json": '{\n  "type": "array"\n}\n',
        "usage_instructions.md": "Do the thing\n",
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_writes_capture_on_parse_failed_when_enabled() -> None:
    correlation_id = uuid4()
    with _bound_correlation_id(correlation_id):
        settings = Settings(LLM_CHAT_OPS_ENABLED=True, LLM_CAPTURE_ON_ERROR_ENABLED=True)
        provider = MagicMock(spec=ChatOpsProviderProtocol)
        provider.complete_chat_ops = AsyncMock(
            return_value=LLMChatOpsResponse(
                content="not-json",
                finish_reason=None,
                raw_payload={"choices": []},
            )
        )

        providers = MagicMock()
        providers.primary = provider
        providers.fallback = None
        providers.fallback_is_remote = False

        sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
        sessions.get = AsyncMock(return_value=None)
        sessions.get_or_create = AsyncMock()

        turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
        turns.list_tail = AsyncMock(return_value=[])
        turns.cancel_pending_turn = AsyncMock(return_value=None)
        turns.create_turn = AsyncMock()
        turns.update_status = AsyncMock(return_value=None)

        messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
        messages.list_by_turn_ids = AsyncMock(return_value=[])
        messages.create_message = AsyncMock()
        messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

        clock = MagicMock(spec=ClockProtocol)
        clock.now.return_value = datetime(2025, 1, 1, tzinfo=timezone.utc)
        id_generator = MagicMock(spec=IdGeneratorProtocol)
        turn_id = uuid4()
        user_message_id = uuid4()
        assistant_message_id = uuid4()
        session_id = uuid4()
        id_generator.new_uuid.side_effect = [
            turn_id,
            user_message_id,
            assistant_message_id,
            session_id,
        ]

        actor = make_user(role=Role.CONTRIBUTOR)
        tool_id = uuid4()
        session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
        sessions.get_or_create.return_value = session
        turns.create_turn.return_value = _make_turn(
            turn_id=turn_id,
            tool_session_id=session.id,
            correlation_id=correlation_id,
        )

        capture_store = MagicMock(spec=LlmCaptureStoreProtocol)
        capture_store.write_capture = AsyncMock()

        handler = EditOpsHandler(
            settings=settings,
            providers=providers,
            budget_resolver=DummyChatOpsBudgetResolver(settings),
            guard=DummyChatGuard(),
            failover=DummyFailover(),
            capture_store=capture_store,
            uow=DummyUow(),
            sessions=sessions,
            turns=turns,
            messages=messages,
            clock=clock,
            id_generator=id_generator,
            token_counters=FakeTokenCounterResolver(),
            system_prompt_loader=lambda _: "prompt",
        )

        result = await handler.handle(
            actor=actor,
            command=EditOpsCommand(
                tool_id=tool_id,
                message="Hej",
                active_file="tool.py",
                selection=None,
                cursor=None,
                virtual_files=_virtual_files(),
            ),
        )

        assert result.enabled is True
        assert result.ops == []

        messages.update_message_content_if_pending_turn.assert_awaited_once()
        turns.update_status.assert_awaited_once()

        capture_store.write_capture.assert_awaited_once()
        kwargs = capture_store.write_capture.await_args.kwargs
        assert kwargs["kind"] == "chat_ops_response"
        assert kwargs["capture_id"] == correlation_id
        payload = kwargs["payload"]
        assert payload["outcome"] == "parse_failed"
        assert payload["tool_id"] == str(tool_id)
        assert payload["extracted_content"] == "not-json"
