from pathlib import Path
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import ToolRun
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api

from .models import ArtifactEntry, EditorRunDetails

router = APIRouter()


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


def _build_run_details(*, run: ToolRun, settings: Settings) -> EditorRunDetails:
    if run.started_at is None:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Run missing started_at",
            details={"run_id": str(run.id)},
        )
    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest or {"artifacts": []})
    artifacts = [
        ArtifactEntry(
            artifact_id=a.artifact_id,
            path=a.path,
            bytes=a.bytes,
            download_url=f"/api/v1/editor/tool-runs/{run.id}/artifacts/{a.artifact_id}",
        )
        for a in manifest.artifacts
    ]
    ui_payload = None
    if run.ui_payload is not None:
        ui_payload = run.ui_payload.model_dump(mode="json")

    stdout_bytes = None
    stdout_max_bytes = None
    stdout_truncated = None
    if run.stdout is not None:
        stdout_bytes = len(run.stdout.encode("utf-8"))
        stdout_max_bytes = settings.RUN_OUTPUT_MAX_STDOUT_BYTES
        stdout_truncated = stdout_bytes >= stdout_max_bytes

    stderr_bytes = None
    stderr_max_bytes = None
    stderr_truncated = None
    if run.stderr is not None:
        stderr_bytes = len(run.stderr.encode("utf-8"))
        stderr_max_bytes = settings.RUN_OUTPUT_MAX_STDERR_BYTES
        stderr_truncated = stderr_bytes >= stderr_max_bytes

    return EditorRunDetails(
        run_id=run.id,
        version_id=run.version_id,
        snapshot_id=run.snapshot_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_summary=run.error_summary,
        stdout=run.stdout,
        stderr=run.stderr,
        stdout_bytes=stdout_bytes,
        stderr_bytes=stderr_bytes,
        stdout_max_bytes=stdout_max_bytes,
        stderr_max_bytes=stderr_max_bytes,
        stdout_truncated=stdout_truncated,
        stderr_truncated=stderr_truncated,
        ui_payload=ui_payload,
        artifacts=artifacts,
    )


@router.get("/tool-runs/{run_id}", response_model=EditorRunDetails)
@inject
async def get_run(
    run_id: UUID,
    runs: FromDishka[ToolRunRepositoryProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_contributor_api),
) -> EditorRunDetails:
    run = await _load_run_for_actor(runs=runs, run_id=run_id, actor=user)
    return _build_run_details(run=run, settings=settings)


@router.get("/tool-runs/{run_id}/artifacts/{artifact_id}")
@inject
async def download_artifact(
    run_id: UUID,
    artifact_id: str,
    settings: FromDishka[Settings],
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_contributor_api),
):
    run = await _load_run_for_actor(runs=runs, run_id=run_id, actor=user)

    manifest = ArtifactsManifest.model_validate(run.artifacts_manifest or {"artifacts": []})
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
