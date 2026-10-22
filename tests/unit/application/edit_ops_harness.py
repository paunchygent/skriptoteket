"""Shared construction for edit-ops handler tests.

Purpose:
    Build an ``EditOpsHandler`` over a mocked chat-ops provider and mocked
    session repositories, so each test states only the provider answer and the
    assertions that matter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from skriptoteket.application.editor.edit_ops_handler import EditOpsHandler
from skriptoteket.application.editor.edit_ops_payload_parser import DefaultEditOpsPayloadParser
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurn
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatInFlightGuardProtocol,
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProviderProtocol,
    VirtualFileId,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.application_fixtures import FakeTokenCounterResolver

_NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


class DummyUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> "DummyUow":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class RecordingChatGuard(ChatInFlightGuardProtocol):
    def __init__(self) -> None:
        self.acquired: list[tuple[UUID, UUID]] = []
        self.released: list[tuple[UUID, UUID]] = []

    async def try_acquire(self, *, user_id: UUID, tool_id: UUID) -> bool:
        self.acquired.append((user_id, tool_id))
        return True

    async def release(self, *, user_id: UUID, tool_id: UUID) -> None:
        self.released.append((user_id, tool_id))


class DummyChatOpsBudgetResolver(ChatOpsBudgetResolverProtocol):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve_chat_ops_budget(self) -> ChatOpsBudget:
        return ChatOpsBudget(
            context_window_tokens=self._settings.LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS,
            max_output_tokens=self._settings.LLM_CHAT_OPS_MAX_TOKENS,
        )


def make_settings(**overrides: object) -> Settings:
    """Settings with the door key the enabled AI features require."""

    return Settings(HULEEDU_INTERNAL_API_KEY="test-internal-key", **overrides)  # type: ignore[arg-type]


def virtual_files() -> dict[VirtualFileId, str]:
    return {
        "tool.py": "print('hi')\n",
        "entrypoint.txt": "run_tool\n",
        "settings_schema.json": '{\n  "type": "object"\n}\n',
        "input_schema.json": '{\n  "type": "array"\n}\n',
        "usage_instructions.md": "Do the thing\n",
    }


@dataclass
class EditOpsHarness:
    """A handler plus the mocks a test asserts on."""

    settings: Settings
    provider: MagicMock
    guard: RecordingChatGuard
    capture_store: MagicMock
    sessions: MagicMock
    turns: MagicMock
    messages: MagicMock
    turn_id: UUID
    tool_id: UUID
    handler: EditOpsHandler = field(init=False)

    def build_handler(self, *, actor_id: UUID) -> None:
        session = ToolSession(
            id=uuid4(),
            tool_id=self.tool_id,
            user_id=actor_id,
            context="editor_chat",
            state={},
            state_rev=0,
            created_at=_NOW,
            updated_at=_NOW,
        )
        self.sessions.get_or_create.return_value = session
        self.turns.create_turn.return_value = ToolSessionTurn(
            id=self.turn_id,
            tool_session_id=session.id,
            status="pending",
            failure_outcome=None,
            provider=None,
            correlation_id=None,
            sequence=1,
            created_at=_NOW,
            updated_at=_NOW,
        )
        clock = MagicMock(spec=ClockProtocol)
        clock.now.return_value = _NOW
        id_generator = MagicMock(spec=IdGeneratorProtocol)
        id_generator.new_uuid.side_effect = [uuid4(), self.turn_id, uuid4(), uuid4()]
        self.handler = EditOpsHandler(
            settings=self.settings,
            provider=self.provider,
            budget_resolver=DummyChatOpsBudgetResolver(self.settings),
            payload_parser=DefaultEditOpsPayloadParser(),
            guard=self.guard,
            capture_store=self.capture_store,
            uow=DummyUow(),
            sessions=self.sessions,
            turns=self.turns,
            messages=self.messages,
            clock=clock,
            id_generator=id_generator,
            token_counters=FakeTokenCounterResolver(),
            system_prompt_loader=lambda _: "prompt",
        )


def make_harness(*, settings: Settings, actor_id: UUID) -> EditOpsHarness:
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()

    turns = MagicMock(spec=ToolSessionTurnRepositoryProtocol)
    turns.list_tail = AsyncMock(return_value=[])
    turns.cancel_pending_turn = AsyncMock(return_value=None)
    turns.update_status = AsyncMock(return_value=None)
    turns.create_turn = AsyncMock()

    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_by_turn_ids = AsyncMock(return_value=[])
    messages.create_message = AsyncMock()
    messages.update_message_content_if_pending_turn = AsyncMock(return_value=True)

    capture_store = MagicMock(spec=LlmCaptureStoreProtocol)
    capture_store.write_capture = AsyncMock()

    harness = EditOpsHarness(
        settings=settings,
        provider=MagicMock(spec=ChatOpsProviderProtocol),
        guard=RecordingChatGuard(),
        capture_store=capture_store,
        sessions=sessions,
        turns=turns,
        messages=messages,
        turn_id=uuid4(),
        tool_id=uuid4(),
    )
    harness.provider.complete_chat_ops = AsyncMock()
    harness.build_handler(actor_id=actor_id)
    return harness
