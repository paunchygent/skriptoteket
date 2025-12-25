"""Tests for sandbox session endpoints (ADR-0038)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.interactive_sandbox import StartSandboxActionResult
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.scripting import (
    StartSandboxActionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.web.api.v1 import editor
from tests.unit.web.admin_scripting_test_support import _tool, _user, _version


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


def _tool_session(
    *,
    tool_id,
    user_id,
    context: str,
    state: dict | None = None,
    state_rev: int = 1,
) -> ToolSession:
    """Create a ToolSession for testing."""
    now = datetime.now(timezone.utc)
    return ToolSession(
        id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        state=state or {},
        state_rev=state_rev,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_sandbox_session_success_returns_state_and_rev() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    session_state = {"step": 2, "data": {"key": "value"}}
    session = _tool_session(
        tool_id=tool.id,
        user_id=user.id,
        context=f"sandbox:{version.id}",
        state=session_state,
        state_rev=3,
    )
    versions_repo.get_by_id.return_value = version
    sessions.get.return_value = session

    result = await _unwrap_dishka(editor.get_sandbox_session)(
        version_id=version.id,
        versions_repo=versions_repo,
        sessions=sessions,
        user=user,
    )

    assert isinstance(result, editor.SandboxSessionResponse)
    assert result.state_rev == 3
    assert result.state == session_state

    versions_repo.get_by_id.assert_awaited_once_with(version_id=version.id)
    sessions.get.assert_awaited_once_with(
        tool_id=tool.id,
        user_id=user.id,
        context=f"sandbox:{version.id}",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_sandbox_session_when_session_not_found_raises_domain_error() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    versions_repo.get_by_id.return_value = version
    sessions.get.return_value = None

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor.get_sandbox_session)(
            version_id=version.id,
            versions_repo=versions_repo,
            sessions=sessions,
            user=user,
        )

    assert exc_info.value.code.value == "NOT_FOUND"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_success_returns_run_id_and_state_rev() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=StartSandboxActionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    run_id = uuid4()
    versions_repo.get_by_id.return_value = version
    handler.handle.return_value = StartSandboxActionResult(
        run_id=run_id,
        state_rev=5,
    )

    result = await _unwrap_dishka(editor.start_sandbox_action)(
        version_id=version.id,
        payload=editor.StartSandboxActionRequest(
            action_id="next_step",
            input={"choice": "A"},
            expected_state_rev=4,
        ),
        versions_repo=versions_repo,
        handler=handler,
        user=user,
        _=None,
    )

    assert isinstance(result, editor.StartSandboxActionResponse)
    assert result.run_id == run_id
    assert result.state_rev == 5

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.version_id == version.id
    assert command.action_id == "next_step"
    assert command.input == {"choice": "A"}
    assert command.expected_state_rev == 4
