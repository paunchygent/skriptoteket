"""Tests for sandbox session endpoints (ADR-0038)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import RunSandboxResult
from skriptoteket.application.scripting.interactive_sandbox import StartSandboxActionResult
from skriptoteket.application.scripting.session_files import (
    ListSandboxSessionFilesResult,
    SessionFileInfo,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import RunContext, VersionState, start_tool_version_run
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.scripting import (
    ListSandboxSessionFilesHandlerProtocol,
    RunSandboxHandlerProtocol,
    StartSandboxActionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.web.api.v1 import editor
from skriptoteket.web.api.v1.editor import sandbox as editor_sandbox
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


def _snapshot_payload_json(
    *,
    entrypoint: str = "run_tool",
    source_code: str = "print('hi')",
) -> str:
    return json.dumps(
        {
            "entrypoint": entrypoint,
            "source_code": source_code,
            "settings_schema": None,
            "input_schema": None,
            "usage_instructions": None,
        }
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
        snapshot_id=None,
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
            snapshot_id=None,
        )

    assert exc_info.value.code.value == "NOT_FOUND"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_sandbox_session_files_calls_handler() -> None:
    handler = AsyncMock(spec=ListSandboxSessionFilesHandlerProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    version_id = uuid4()
    snapshot_id = uuid4()
    tool_id = uuid4()

    handler.handle.return_value = ListSandboxSessionFilesResult(
        tool_id=tool_id,
        version_id=version_id,
        snapshot_id=snapshot_id,
        files=[SessionFileInfo(name="input.txt", bytes=42)],
    )

    result = await _unwrap_dishka(editor_sandbox.list_sandbox_session_files)(
        version_id=version_id,
        handler=handler,
        user=user,
        snapshot_id=snapshot_id,
    )

    assert result.tool_id == tool_id
    assert result.version_id == version_id
    assert result.snapshot_id == snapshot_id
    assert result.files[0].name == "input.txt"

    handler.handle.assert_awaited_once()
    handler_kwargs = handler.handle.call_args.kwargs
    assert handler_kwargs["actor"] == user
    assert handler_kwargs["query"].version_id == version_id
    assert handler_kwargs["query"].snapshot_id == snapshot_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_valid_snapshot_payload_calls_handler() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    run_id = uuid4()
    snapshot_id = uuid4()
    now = datetime.now(timezone.utc)
    run = start_tool_version_run(
        run_id=run_id,
        tool_id=tool.id,
        version_id=version.id,
        snapshot_id=snapshot_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=user.id,
        workdir_path=str(run_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        input_values={},
        now=now,
    )
    versions_repo.get_by_id.return_value = version
    handler.handle.return_value = RunSandboxResult(
        run=run,
        state_rev=2,
        snapshot_id=snapshot_id,
    )

    result = await _unwrap_dishka(editor.run_sandbox)(
        version_id=version.id,
        handler=handler,
        versions_repo=versions_repo,
        settings=Settings(),
        user=user,
        _=None,
        files=None,
        inputs=None,
        snapshot=_snapshot_payload_json(),
    )

    assert isinstance(result, editor.SandboxRunResponse)
    assert result.run_id == run_id
    assert result.snapshot_id == snapshot_id
    assert result.state_rev == 2

    handler.handle.assert_awaited_once()
    command = handler.handle.call_args.kwargs["command"]
    assert command.tool_id == tool.id
    assert command.version_id == version.id
    assert command.snapshot_payload.entrypoint == "run_tool"
    assert command.input_files == []
    assert command.input_values == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_invalid_snapshot_json_raises_domain_error() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    versions_repo.get_by_id.return_value = version

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor.run_sandbox)(
            version_id=version.id,
            handler=handler,
            versions_repo=versions_repo,
            settings=Settings(),
            user=user,
            _=None,
            files=None,
            inputs=None,
            snapshot="{bad json",
        )

    assert exc_info.value.code.value == "VALIDATION_ERROR"
    assert exc_info.value.message == "snapshot must be valid JSON"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_snapshot_schema_error_raises_domain_error() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    versions_repo.get_by_id.return_value = version

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor.run_sandbox)(
            version_id=version.id,
            handler=handler,
            versions_repo=versions_repo,
            settings=Settings(),
            user=user,
            _=None,
            files=None,
            inputs=None,
            snapshot=_snapshot_payload_json(entrypoint=""),
        )

    assert exc_info.value.code.value == "VALIDATION_ERROR"
    assert exc_info.value.message == "snapshot must be valid JSON"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_inputs_invalid_json_raises_domain_error() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    versions_repo.get_by_id.return_value = version

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor.run_sandbox)(
            version_id=version.id,
            handler=handler,
            versions_repo=versions_repo,
            settings=Settings(),
            user=user,
            _=None,
            files=None,
            inputs="not-json",
            snapshot=_snapshot_payload_json(),
        )

    assert exc_info.value.code.value == "VALIDATION_ERROR"
    assert exc_info.value.message == "inputs must be valid JSON"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_inputs_not_object_raises_domain_error() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    versions_repo.get_by_id.return_value = version

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor.run_sandbox)(
            version_id=version.id,
            handler=handler,
            versions_repo=versions_repo,
            settings=Settings(),
            user=user,
            _=None,
            files=None,
            inputs='["a"]',
            snapshot=_snapshot_payload_json(),
        )

    assert exc_info.value.code.value == "VALIDATION_ERROR"
    assert exc_info.value.message == "inputs must be a JSON object"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_sandbox_action_success_returns_run_id_and_state_rev() -> None:
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    handler = AsyncMock(spec=StartSandboxActionHandlerProtocol)
    tool = _tool()
    user = _user(role=Role.CONTRIBUTOR)
    version = _version(tool_id=tool.id, created_by_user_id=user.id, state=VersionState.DRAFT)
    run_id = uuid4()
    snapshot_id = uuid4()
    versions_repo.get_by_id.return_value = version
    handler.handle.return_value = StartSandboxActionResult(
        run_id=run_id,
        state_rev=5,
    )

    result = await _unwrap_dishka(editor.start_sandbox_action)(
        version_id=version.id,
        payload=editor.StartSandboxActionRequest(
            snapshot_id=snapshot_id,
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
    assert command.snapshot_id == snapshot_id
    assert command.action_id == "next_step"
    assert command.input == {"choice": "A"}
    assert command.expected_state_rev == 4
