from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.editor.edit_ops_handler import EditOpsHandler
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatInFlightGuardProtocol,
    ChatOpsProviderProtocol,
    EditOpsCommand,
    EditOpsResult,
    LLMChatOpsResponse,
    VirtualFileId,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
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


def _virtual_files() -> dict[VirtualFileId, str]:
    return {
        "tool.py": "print('hi')\n",
        "entrypoint.txt": "run_tool\n",
        "settings_schema.json": '{\n  "type": "object"\n}\n',
        "input_schema.json": '{\n  "type": "array"\n}\n',
        "usage_instructions.md": "Do the thing\n",
    }


def _fingerprint(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_returns_disabled_when_disabled() -> None:
    settings = Settings(LLM_CHAT_OPS_ENABLED=False)
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _: "prompt",
    )
    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()

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

    assert isinstance(result, EditOpsResult)
    assert result.enabled is False
    assert result.ops == []
    provider.complete_chat_ops.assert_not_called()
    messages.append_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_over_budget_does_not_mutate_thread() -> None:
    settings = Settings(
        LLM_CHAT_OPS_ENABLED=True,
        LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS=8,
        LLM_CHAT_OPS_MAX_TOKENS=8,
        LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS=2,
    )
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[])
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
    sessions.get_or_create.return_value = session

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    provider.complete_chat_ops.assert_not_called()
    messages.append_message.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_parses_valid_response_and_persists_messages() -> None:
    settings = Settings(LLM_CHAT_OPS_ENABLED=True)
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[])
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
    sessions.get_or_create.return_value = session
    id_generator.new_uuid.side_effect = [uuid4(), uuid4(), uuid4()]

    response_payload = (
        '{"assistant_message":"Klart.","ops":[{"op":"replace","target_file":"tool.py",'
        '"target":{"kind":"document"},"content":"print(\\"hej\\")\\n"}]}'
    )
    provider.complete_chat_ops = AsyncMock(
        return_value=LLMChatOpsResponse(content=response_payload, finish_reason=None)
    )

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _: "prompt",
    )

    result = await handler.handle(
        actor=actor,
        command=EditOpsCommand(
            tool_id=tool_id,
            message="Uppdatera koden",
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=_virtual_files(),
        ),
    )

    assert result.enabled is True
    assert result.assistant_message == "Klart."
    assert len(result.ops) == 1
    assert result.ops[0].op == "replace"
    assert messages.append_message.await_count == 2
    assert result.base_fingerprints["tool.py"] == _fingerprint("print('hi')\n")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_rejects_cursor_ops_when_cursor_missing() -> None:
    settings = Settings(LLM_CHAT_OPS_ENABLED=True)
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[])
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
    sessions.get_or_create.return_value = session
    id_generator.new_uuid.side_effect = [uuid4(), uuid4(), uuid4()]

    response_payload = (
        '{"assistant_message":"Klart.","ops":[{"op":"insert","target_file":"tool.py",'
        '"target":{"kind":"cursor"},"content":"# TODO\\n"}]}'
    )
    provider.complete_chat_ops = AsyncMock(
        return_value=LLMChatOpsResponse(content=response_payload, finish_reason=None)
    )

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _: "prompt",
    )

    result = await handler.handle(
        actor=actor,
        command=EditOpsCommand(
            tool_id=tool_id,
            message="Lägg till en rad",
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=_virtual_files(),
        ),
    )

    assert result.enabled is True
    assert result.ops == []
    assert (
        result.assistant_message == "Jag kunde inte skapa ett giltigt ändringsförslag. Försök igen."
    )
    assert messages.append_message.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_parses_valid_patch_ops() -> None:
    settings = Settings(LLM_CHAT_OPS_ENABLED=True)
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[])
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
    sessions.get_or_create.return_value = session
    id_generator.new_uuid.side_effect = [uuid4(), uuid4(), uuid4()]

    patch = (
        "diff --git a/tool.py b/tool.py\n"
        "--- a/tool.py\n"
        "+++ b/tool.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-print('hi')\n"
        "+print('hej')\n"
    )
    response_payload = json.dumps(
        {
            "assistant_message": "Klart.",
            "ops": [{"op": "patch", "target_file": "tool.py", "patch": patch}],
        },
        ensure_ascii=False,
    )
    provider.complete_chat_ops = AsyncMock(
        return_value=LLMChatOpsResponse(content=response_payload, finish_reason=None)
    )

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        system_prompt_loader=lambda _: "prompt",
    )

    result = await handler.handle(
        actor=actor,
        command=EditOpsCommand(
            tool_id=tool_id,
            message="Byt texten",
            active_file="tool.py",
            selection=None,
            cursor=None,
            virtual_files=_virtual_files(),
        ),
    )

    assert result.enabled is True
    assert len(result.ops) == 1
    assert result.ops[0].op == "patch"
    assert messages.append_message.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_invalid_json_returns_empty_ops() -> None:
    settings = Settings(LLM_CHAT_OPS_ENABLED=True)
    provider = MagicMock(spec=ChatOpsProviderProtocol)
    sessions = MagicMock(spec=ToolSessionRepositoryProtocol)
    sessions.get = AsyncMock(return_value=None)
    sessions.get_or_create = AsyncMock()
    messages = MagicMock(spec=ToolSessionMessageRepositoryProtocol)
    messages.list_tail = AsyncMock(return_value=[])
    messages.append_message = AsyncMock()
    clock = MagicMock(spec=ClockProtocol)
    id_generator = MagicMock(spec=IdGeneratorProtocol)

    actor = make_user(role=Role.CONTRIBUTOR)
    tool_id = uuid4()
    session = _make_tool_session(tool_id=tool_id, user_id=actor.id)
    sessions.get_or_create.return_value = session
    id_generator.new_uuid.side_effect = [uuid4(), uuid4(), uuid4()]

    provider.complete_chat_ops = AsyncMock(
        return_value=LLMChatOpsResponse(content="not-json", finish_reason=None)
    )

    handler = EditOpsHandler(
        settings=settings,
        provider=provider,
        guard=DummyChatGuard(),
        uow=DummyUow(),
        sessions=sessions,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
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
    assert result.assistant_message != ""
    assert messages.append_message.await_count == 2
