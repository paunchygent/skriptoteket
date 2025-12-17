from __future__ import annotations

import io
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile
from starlette.requests import Request
from starlette.responses import FileResponse

from skriptoteket.application.scripting.commands import RunSandboxResult
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, Session, User
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolRun,
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    RunSandboxHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.pages import admin_scripting_runs


def _original(fn: Any) -> Any:
    return getattr(fn, "__dishka_orig_func__", fn)


def _request(*, path: str, method: str = "GET", headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": raw_headers,
        "query_string": b"",
    }
    return Request(scope)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: Role) -> User:
    now = _now()
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _session(*, user_id: uuid.UUID) -> Session:
    now = _now()
    return Session(
        id=uuid.uuid4(),
        user_id=user_id,
        csrf_token="csrf",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )


def _tool(*, tool_id: uuid.UUID | None = None, title: str = "Tool") -> Tool:
    now = _now()
    return Tool(
        id=tool_id or uuid.uuid4(),
        slug="tool",
        title=title,
        summary="Summary",
        is_published=False,
        active_version_id=None,
        created_at=now,
        updated_at=now,
    )


def _version(*, version_id: uuid.UUID, tool_id: uuid.UUID, created_by: uuid.UUID) -> ToolVersion:
    now = _now()
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=1,
        state=VersionState.DRAFT,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=created_by,
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )


def _run(
    *,
    run_id: uuid.UUID,
    tool_id: uuid.UUID,
    version_id: uuid.UUID,
    requested_by: uuid.UUID,
    artifacts: list[dict[str, object]] | None = None,
) -> ToolRun:
    now = _now()
    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.SANDBOX,
        requested_by_user_id=requested_by,
        status=RunStatus.SUCCEEDED,
        started_at=now,
        finished_at=now,
        workdir_path="/tmp/run",
        input_filename="input.bin",
        input_size_bytes=3,
        html_output="<p>ok</p>",
        stdout="",
        stderr="",
        artifacts_manifest={"artifacts": artifacts or []},
        error_summary=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_raises_validation_error_when_tool_id_invalid() -> None:
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    request = _request(path="/admin/tool-versions/x/run-sandbox", method="POST")
    file = UploadFile(filename="input.bin", file=io.BytesIO(b"abc"))

    with pytest.raises(DomainError) as exc_info:
        await _original(admin_scripting_runs.run_sandbox)(
            request=request,
            version_id=uuid.uuid4(),
            handler=handler,
            tools=tools,
            maintainers=maintainers,
            versions_repo=versions_repo,
            user=user,
            session=None,
            tool_id="not-a-uuid",
            file=file,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_hx_request_domain_error_returns_inline_html() -> None:
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    handler.handle.side_effect = DomainError(code=ErrorCode.VALIDATION_ERROR, message="Bad")
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    request = _request(
        path="/admin/tool-versions/x/run-sandbox",
        method="POST",
        headers={"HX-Request": "true"},
    )
    file = UploadFile(filename="input.bin", file=io.BytesIO(b"abc"))

    response = await _original(admin_scripting_runs.run_sandbox)(
        request=request,
        version_id=uuid.uuid4(),
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=None,
        tool_id=str(uuid.uuid4()),
        file=file,
    )

    assert response.status_code == 400
    assert '<p class="error">' in response.body.decode("utf-8")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_hx_request_success_renders_run_result_partial() -> None:
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    tool_id = uuid.uuid4()
    version_id = uuid.uuid4()
    run_id = uuid.uuid4()
    run = _run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by=user.id,
        artifacts=[{"artifact_id": "a1", "path": "output/result.bin", "bytes": 3}],
    )
    handler.handle.return_value = RunSandboxResult(run=run)

    request = _request(
        path=f"/admin/tool-versions/{version_id}/run-sandbox",
        method="POST",
        headers={"HX-Request": "true"},
    )
    file = UploadFile(filename="", file=io.BytesIO(b"abc"))

    response = await _original(admin_scripting_runs.run_sandbox)(
        request=request,
        version_id=version_id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=None,
        tool_id=str(tool_id),
        file=file,
    )

    assert response.status_code == 200
    assert response.template.name == "admin/partials/run_result_with_toast.html"
    assert response.context["run"] == run
    assert response.context["artifacts"][0]["download_url"] == (
        f"/admin/tool-runs/{run.id}/artifacts/a1"
    )

    called_command = handler.handle.call_args.kwargs["command"]
    assert called_command.tool_id == tool_id
    assert called_command.version_id == version_id
    assert called_command.input_filename == "input.bin"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_sandbox_non_hx_success_renders_editor_with_run() -> None:
    handler = AsyncMock(spec=RunSandboxHandlerProtocol)
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)

    user = _user(role=Role.ADMIN)
    session = _session(user_id=user.id)

    tool_id = uuid.uuid4()
    version_id = uuid.uuid4()
    tool = _tool(tool_id=tool_id)
    version = _version(version_id=version_id, tool_id=tool_id, created_by=user.id)
    run = _run(
        run_id=uuid.uuid4(),
        tool_id=tool_id,
        version_id=version_id,
        requested_by=user.id,
        artifacts=[],
    )

    handler.handle.return_value = RunSandboxResult(run=run)
    versions_repo.get_by_id.return_value = version
    tools.get_by_id.return_value = tool
    versions_repo.list_for_tool.return_value = [version]

    request = _request(path=f"/admin/tool-versions/{version_id}/run-sandbox", method="POST")
    file = UploadFile(filename="input.bin", file=io.BytesIO(b"abc"))

    response = await _original(admin_scripting_runs.run_sandbox)(
        request=request,
        version_id=version_id,
        handler=handler,
        tools=tools,
        maintainers=maintainers,
        versions_repo=versions_repo,
        user=user,
        session=session,
        tool_id=str(tool_id),
        file=file,
    )

    assert response.status_code == 200
    assert response.template.name == "admin/script_editor.html"
    assert response.context["csrf_token"] == session.csrf_token
    assert response.context["run"] == run
    assert response.context["error"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_renders_run_partial_for_owner() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    user = _user(role=Role.CONTRIBUTOR)

    run = _run(
        run_id=uuid.uuid4(),
        tool_id=uuid.uuid4(),
        version_id=uuid.uuid4(),
        requested_by=user.id,
        artifacts=[],
    )
    runs.get_by_id.return_value = run

    request = _request(path=f"/admin/tool-runs/{run.id}")

    response = await _original(admin_scripting_runs.get_run)(
        request=request,
        run_id=run.id,
        runs=runs,
        user=user,
    )

    assert response.status_code == 200
    assert response.template.name == "admin/partials/run_result_with_toast.html"
    assert response.context["run"] == run


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_run_raises_not_found_when_missing() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_by_id.return_value = None

    user = _user(role=Role.ADMIN)
    request = _request(path="/admin/tool-runs/x")

    with pytest.raises(DomainError) as exc_info:
        await _original(admin_scripting_runs.get_run)(
            request=request,
            run_id=uuid.uuid4(),
            runs=runs,
            user=user,
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_artifact_returns_file_response(tmp_path: Path) -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    user = _user(role=Role.CONTRIBUTOR)

    run_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    version_id = uuid.uuid4()
    artifact_id = "a1"
    run = _run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        requested_by=user.id,
        artifacts=[{"artifact_id": artifact_id, "path": "output/result.bin", "bytes": 3}],
    )
    runs.get_by_id.return_value = run

    settings = Settings(ARTIFACTS_ROOT=(tmp_path / "artifacts"))
    run_dir = settings.ARTIFACTS_ROOT / str(run_id) / "output"
    run_dir.mkdir(parents=True, exist_ok=True)
    file_path = run_dir / "result.bin"
    file_path.write_bytes(b"abc")

    response = await _original(admin_scripting_runs.download_artifact)(
        request=_request(path="/ignored"),
        run_id=run_id,
        artifact_id=artifact_id,
        settings=settings,
        runs=runs,
        user=user,
    )

    assert isinstance(response, FileResponse)
    assert response.status_code == 200
    assert response.media_type == "application/octet-stream"
    assert 'filename="result.bin"' in response.headers.get("content-disposition", "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_run_for_actor_rejects_other_contributor() -> None:
    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    actor = _user(role=Role.CONTRIBUTOR)
    other_user_id = uuid.uuid4()
    run = _run(
        run_id=uuid.uuid4(),
        tool_id=uuid.uuid4(),
        version_id=uuid.uuid4(),
        requested_by=other_user_id,
        artifacts=[],
    )
    runs.get_by_id.return_value = run

    with pytest.raises(DomainError) as exc_info:
        await admin_scripting_runs._load_run_for_actor(
            runs=runs,
            run_id=run.id,
            actor=actor,
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN


@pytest.mark.unit
def test_resolve_artifact_path_rejects_symlink_escape(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    run_id = uuid.uuid4()
    run_dir = artifacts_root / str(run_id)
    run_dir.mkdir(parents=True)

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.bin").write_bytes(b"abc")
    (run_dir / "output").symlink_to(outside, target_is_directory=True)

    settings = Settings(ARTIFACTS_ROOT=artifacts_root)

    with pytest.raises(DomainError) as exc_info:
        admin_scripting_runs._resolve_artifact_path(
            settings=settings,
            run_id=run_id,
            artifact_path="output/result.bin",
        )

    assert exc_info.value.code is ErrorCode.INTERNAL_ERROR
