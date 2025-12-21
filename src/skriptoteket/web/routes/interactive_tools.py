from pathlib import Path
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, Response

from skriptoteket.application.scripting.interactive_tools import (
    GetRunQuery,
    GetRunResult,
    GetSessionStateQuery,
    GetSessionStateResult,
    ListArtifactsQuery,
    ListArtifactsResult,
    StartActionCommand,
    StartActionResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunContext, ToolRun
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.interactive_tools import (
    GetRunHandlerProtocol,
    GetSessionStateHandlerProtocol,
    ListArtifactsHandlerProtocol,
    StartActionHandlerProtocol,
)
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.auth.dependencies import require_user

router = APIRouter(prefix="/api")


async def _load_production_run_for_user(
    *,
    runs: ToolRunRepositoryProtocol,
    run_id: UUID,
    actor: User,
) -> ToolRun:
    run = await runs.get_by_id(run_id=run_id)
    if run is None or run.requested_by_user_id != actor.id:
        raise not_found("ToolRun", str(run_id))
    if run.context is not RunContext.PRODUCTION:
        raise not_found("ToolRun", str(run_id))
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


@router.post("/start_action", response_model=StartActionResult)
@inject
async def start_action(
    command: StartActionCommand,
    handler: FromDishka[StartActionHandlerProtocol],
    user: User = Depends(require_user),
) -> StartActionResult:
    return await handler.handle(actor=user, command=command)


@router.get("/tools/{tool_id}/sessions/{context}", response_model=GetSessionStateResult)
@inject
async def get_session_state(
    tool_id: UUID,
    context: str,
    handler: FromDishka[GetSessionStateHandlerProtocol],
    user: User = Depends(require_user),
) -> GetSessionStateResult:
    return await handler.handle(
        actor=user,
        query=GetSessionStateQuery(tool_id=tool_id, context=context),
    )


@router.get("/runs/{run_id}", response_model=GetRunResult)
@inject
async def get_run(
    run_id: UUID,
    handler: FromDishka[GetRunHandlerProtocol],
    user: User = Depends(require_user),
) -> GetRunResult:
    return await handler.handle(actor=user, query=GetRunQuery(run_id=run_id))


@router.get("/runs/{run_id}/artifacts", response_model=ListArtifactsResult)
@inject
async def list_artifacts(
    run_id: UUID,
    handler: FromDishka[ListArtifactsHandlerProtocol],
    user: User = Depends(require_user),
) -> ListArtifactsResult:
    return await handler.handle(actor=user, query=ListArtifactsQuery(run_id=run_id))


@router.get("/runs/{run_id}/artifacts/{artifact_id}")
@inject
async def download_artifact(
    request: Request,
    run_id: UUID,
    artifact_id: str,
    settings: FromDishka[Settings],
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_user),
) -> Response:
    del request
    run = await _load_production_run_for_user(runs=runs, run_id=run_id, actor=user)

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
