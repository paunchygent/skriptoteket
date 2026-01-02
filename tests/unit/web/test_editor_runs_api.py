from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    finish_run,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.tool_runs import ToolRun
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.api.v1.editor import runs as editor_runs
from tests.unit.web.admin_scripting_test_support import _user


def _unwrap_dishka(fn):
    """Extract original function from Dishka-wrapped handlers."""
    return getattr(fn, "__dishka_orig_func__", fn)


def _finished_run(
    *,
    requested_by_user_id: UUID,
    stdout: str | None,
    stderr: str | None,
) -> ToolRun:
    now = datetime.now(timezone.utc)
    run = start_tool_version_run(
        run_id=uuid4(),
        tool_id=uuid4(),
        version_id=uuid4(),
        snapshot_id=uuid4(),
        context=RunContext.SANDBOX,
        requested_by_user_id=requested_by_user_id,
        workdir_path="workdir",
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        input_values={},
        now=now,
    )
    return finish_run(
        run=run,
        status=RunStatus.SUCCEEDED,
        now=now + timedelta(seconds=1),
        stdout=stdout,
        stderr=stderr,
        artifacts_manifest={"artifacts": []},
        error_summary=None,
        ui_payload=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_returns_stdout_stderr_and_metadata_for_owner() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    settings = Settings()
    stdout = "hello from sandbox"
    stderr = "warning: check input"
    run = _finished_run(requested_by_user_id=user.id, stdout=stdout, stderr=stderr)
    runs.get_by_id.return_value = run

    result = await _unwrap_dishka(editor_runs.get_run)(
        run_id=run.id,
        runs=runs,
        settings=settings,
        user=user,
    )

    assert result.stdout == stdout
    assert result.stderr == stderr
    assert result.stdout_bytes == len(stdout.encode("utf-8"))
    assert result.stderr_bytes == len(stderr.encode("utf-8"))
    assert result.stdout_max_bytes == settings.RUN_OUTPUT_MAX_STDOUT_BYTES
    assert result.stderr_max_bytes == settings.RUN_OUTPUT_MAX_STDERR_BYTES
    assert result.stdout_truncated is False
    assert result.stderr_truncated is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_sets_truncated_when_stdout_exceeds_cap() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    settings = Settings(RUN_OUTPUT_MAX_STDOUT_BYTES=10)
    stdout = "0123456789ABCDEF"
    run = _finished_run(requested_by_user_id=user.id, stdout=stdout, stderr=None)
    runs.get_by_id.return_value = run

    result = await _unwrap_dishka(editor_runs.get_run)(
        run_id=run.id,
        runs=runs,
        settings=settings,
        user=user,
    )

    assert result.stdout_bytes == len(stdout.encode("utf-8"))
    assert result.stdout_max_bytes == 10
    assert result.stdout_truncated is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_for_other_contributor_raises_forbidden() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    user = _user(role=Role.CONTRIBUTOR)
    other_user = _user(role=Role.CONTRIBUTOR)
    run = _finished_run(requested_by_user_id=other_user.id, stdout="ok", stderr=None)
    runs.get_by_id.return_value = run

    with pytest.raises(DomainError) as exc_info:
        await _unwrap_dishka(editor_runs.get_run)(
            run_id=run.id,
            runs=runs,
            settings=Settings(),
            user=user,
        )

    assert exc_info.value.code.value == "FORBIDDEN"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_admin_can_access_other_users_run() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    admin = _user(role=Role.ADMIN)
    other_user = _user(role=Role.CONTRIBUTOR)
    run = _finished_run(requested_by_user_id=other_user.id, stdout="ok", stderr=None)
    runs.get_by_id.return_value = run

    result = await _unwrap_dishka(editor_runs.get_run)(
        run_id=run.id,
        runs=runs,
        settings=Settings(),
        user=admin,
    )

    assert result.run_id == run.id
    assert result.stdout == "ok"
