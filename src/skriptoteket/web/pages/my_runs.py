"""User run history routes.

Routes for users to view their past production runs and download artifacts.
"""

from pathlib import Path
from uuid import UUID

import structlog
from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunContext, ToolRun
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.auth.dependencies import get_current_session, require_user
from skriptoteket.web.templating import templates

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/my-runs")


def _user_artifacts_for_run(run: ToolRun) -> list[dict[str, object]]:
    """Generate artifact list with user-facing download URLs."""
    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
    return [
        {
            "artifact_id": artifact.artifact_id,
            "path": artifact.path,
            "bytes": artifact.bytes,
            "download_url": f"/my-runs/{run.id}/artifacts/{artifact.artifact_id}",
        }
        for artifact in manifest.artifacts
    ]


async def _load_production_run_for_user(
    *,
    runs: ToolRunRepositoryProtocol,
    run_id: UUID,
    user: User,
) -> ToolRun:
    """Load a production run that belongs to the user.

    Returns 404 for:
    - Run not found
    - Run belongs to another user
    - Run is not a production run (sandbox runs are admin-only)
    """
    run = await runs.get_by_id(run_id=run_id)
    if run is None:
        logger.warning("Run not found", run_id=str(run_id), user_id=str(user.id))
        raise not_found("ToolRun", str(run_id))
    if run.requested_by_user_id != user.id:
        logger.warning(
            "Run belongs to different user",
            run_id=str(run_id),
            run_user_id=str(run.requested_by_user_id),
            request_user_id=str(user.id),
        )
        raise not_found("ToolRun", str(run_id))
    if run.context is not RunContext.PRODUCTION:
        logger.warning(
            "Run is not production context",
            run_id=str(run_id),
            context=run.context.value,
        )
        raise not_found("ToolRun", str(run_id))
    return run


def _resolve_artifact_path(
    *,
    settings: Settings,
    run_id: UUID,
    artifact_path: str,
) -> tuple[Path, Path]:
    """Validate and resolve artifact path safely."""
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


@router.get("/{run_id}", response_class=HTMLResponse)
@inject
async def view_run(
    request: Request,
    run_id: UUID,
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_user),
    session: Session | None = Depends(get_current_session),
) -> HTMLResponse:
    """View a past production run result."""
    csrf_token = session.csrf_token if session else ""
    run = await _load_production_run_for_user(runs=runs, run_id=run_id, user=user)

    return templates.TemplateResponse(
        request=request,
        name="my_runs/detail.html",
        context={
            "request": request,
            "user": user,
            "csrf_token": csrf_token,
            "run": run,
            "artifacts": _user_artifacts_for_run(run),
        },
    )


@router.get("/{run_id}/artifacts/{artifact_id}")
@inject
async def download_artifact(
    request: Request,
    run_id: UUID,
    artifact_id: str,
    settings: FromDishka[Settings],
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_user),
) -> Response:
    """Download an artifact from a user's production run."""
    del request
    run = await _load_production_run_for_user(runs=runs, run_id=run_id, user=user)

    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest)
    artifact = next((a for a in manifest.artifacts if a.artifact_id == artifact_id), None)
    if artifact is None:
        logger.warning(
            "Artifact not found in manifest",
            run_id=str(run_id),
            artifact_id=artifact_id,
            available=[a.artifact_id for a in manifest.artifacts],
        )
        raise not_found("Artifact", artifact_id)

    candidate_path, relative_path = _resolve_artifact_path(
        settings=settings,
        run_id=run.id,
        artifact_path=artifact.path,
    )
    file_exists = candidate_path.is_file()
    logger.info(
        "Resolving artifact download",
        run_id=str(run_id),
        artifact_id=artifact_id,
        path=artifact.path,
        candidate=str(candidate_path),
        exists=file_exists,
    )
    if not file_exists:
        raise not_found("ArtifactFile", str(candidate_path))

    return FileResponse(
        candidate_path,
        filename=relative_path.name,
        media_type="application/octet-stream",
    )
