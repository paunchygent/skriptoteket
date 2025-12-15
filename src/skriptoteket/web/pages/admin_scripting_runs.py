from pathlib import Path
from typing import TypedDict
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

from skriptoteket.application.scripting.commands import RunSandboxCommand
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, Session, User
from skriptoteket.domain.scripting.execution import ArtifactsManifest
from skriptoteket.domain.scripting.models import ToolRun
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    RunSandboxHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.dependencies import get_current_session, require_contributor
from skriptoteket.web.pages.admin_scripting_support import (
    artifacts_for_run as _artifacts_for_run,
)
from skriptoteket.web.pages.admin_scripting_support import (
    is_hx_request as _is_hx_request,
)
from skriptoteket.web.pages.admin_scripting_support import (
    parse_uuid as _parse_uuid,
)
from skriptoteket.web.pages.admin_scripting_support import (
    render_editor_for_version_id as _render_editor_for_version_id,
)
from skriptoteket.web.pages.admin_scripting_support import (
    status_code_for_error as _status_code_for_error,
)
from skriptoteket.web.templating import templates
from skriptoteket.web.ui_text import ui_error_message as _ui_error_message

router = APIRouter()


class _SandboxEditorKwargs(TypedDict):
    request: Request
    user: User
    csrf_token: str
    tools: ToolRepositoryProtocol
    versions_repo: ToolVersionRepositoryProtocol
    version_id: UUID


async def _load_run_for_actor(
    *,
    runs: ToolRunRepositoryProtocol,
    run_id: UUID,
    actor: User,
) -> ToolRun:
    run = await runs.get_by_id(run_id=run_id)
    if run is None:
        raise not_found("ToolRun", str(run_id))
    if actor.role is Role.CONTRIBUTOR and run.requested_by_user_id != actor.id:
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Insufficient permissions",
            details={"run_id": str(run.id)},
        )
    return run


def _resolve_artifact_path(
    *,
    settings: Settings,
    run_id: UUID,
    artifact_path: str,
) -> tuple[Path, Path]:
    relative_path = Path(validate_output_path(path=artifact_path).as_posix())
    run_dir = settings.ARTIFACTS_ROOT / str(run_id)
    candidate_path = (run_dir / relative_path).resolve()

    run_root = run_dir.resolve()
    artifacts_root = settings.ARTIFACTS_ROOT.resolve()
    if run_root not in candidate_path.parents:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Artifact path is outside run directory",
            details={"path": artifact_path},
        )
    if artifacts_root not in candidate_path.parents:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Artifact path is outside artifacts root",
            details={"path": artifact_path},
        )

    return candidate_path, relative_path


def _render_hx_error(exc: DomainError) -> HTMLResponse:
    return HTMLResponse(
        f'<p class="error">{_ui_error_message(exc)}</p>',
        status_code=_status_code_for_error(exc),
    )


def _render_run_result_partial(*, request: Request, run: ToolRun) -> Response:
    return templates.TemplateResponse(
        "admin/partials/run_result.html",
        {"request": request, "run": run, "artifacts": _artifacts_for_run(run)},
    )


async def _render_sandbox_editor(
    *,
    request: Request,
    user: User,
    csrf_token: str,
    tools: ToolRepositoryProtocol,
    versions_repo: ToolVersionRepositoryProtocol,
    version_id: UUID,
    run: ToolRun | None,
    error: str | None,
    status_code: int | None = None,
) -> Response:
    return await _render_editor_for_version_id(
        request=request,
        user=user,
        csrf_token=csrf_token,
        tools=tools,
        versions_repo=versions_repo,
        version_id=version_id,
        editor_entrypoint=None,
        editor_source_code=None,
        run=run,
        error=error,
        status_code=status_code,
    )


async def _execute_sandbox_run(
    *,
    handler: RunSandboxHandlerProtocol,
    actor: User,
    tool_id: UUID,
    version_id: UUID,
    file: UploadFile,
) -> ToolRun:
    input_bytes = await file.read()
    result = await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            input_filename=file.filename or "input.bin",
            input_bytes=input_bytes,
        ),
    )
    return result.run


@router.post("/admin/tool-versions/{version_id}/run-sandbox", response_class=HTMLResponse)
@inject
async def run_sandbox(
    request: Request,
    version_id: UUID,
    handler: FromDishka[RunSandboxHandlerProtocol],
    tools: FromDishka[ToolRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor),
    session: Session | None = Depends(get_current_session),
    tool_id: str = Form(...),
    file: UploadFile = File(...),
) -> Response:
    csrf_token = session.csrf_token if session else ""
    hx_request = _is_hx_request(request)
    parsed_tool_id = _parse_uuid(tool_id)
    if parsed_tool_id is None:
        raise validation_error("Invalid tool_id", details={"tool_id": tool_id})

    editor_kwargs: _SandboxEditorKwargs = {
        "request": request,
        "user": user,
        "csrf_token": csrf_token,
        "tools": tools,
        "versions_repo": versions_repo,
        "version_id": version_id,
    }
    try:
        run = await _execute_sandbox_run(
            handler=handler,
            actor=user,
            tool_id=parsed_tool_id,
            version_id=version_id,
            file=file,
        )
    except DomainError as exc:
        if hx_request:
            return _render_hx_error(exc)
        return await _render_sandbox_editor(
            **editor_kwargs,
            run=None,
            error=_ui_error_message(exc),
            status_code=_status_code_for_error(exc),
        )

    if hx_request:
        return _render_run_result_partial(request=request, run=run)
    return await _render_sandbox_editor(**editor_kwargs, run=run, error=None)


@router.get("/admin/tool-runs/{run_id}", response_class=HTMLResponse)
@inject
async def get_run(
    request: Request,
    run_id: UUID,
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_contributor),
) -> Response:
    run = await _load_run_for_actor(runs=runs, run_id=run_id, actor=user)
    return _render_run_result_partial(request=request, run=run)


@router.get("/admin/tool-runs/{run_id}/artifacts/{artifact_id}")
@inject
async def download_artifact(
    request: Request,
    run_id: UUID,
    artifact_id: str,
    settings: FromDishka[Settings],
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_contributor),
) -> Response:
    del request
    run = await _load_run_for_actor(runs=runs, run_id=run_id, actor=user)

    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
    artifact = next((a for a in manifest.artifacts if a.artifact_id == artifact_id), None)
    if artifact is None:
        raise not_found("Artifact", artifact_id)

    candidate_path, relative_path = _resolve_artifact_path(
        settings=settings,
        run_id=run.id,
        artifact_path=artifact.path,
    )
    if not candidate_path.is_file():
        raise not_found("ArtifactFile", str(candidate_path))

    return FileResponse(
        candidate_path,
        filename=relative_path.name,
        media_type="application/octet-stream",
    )
