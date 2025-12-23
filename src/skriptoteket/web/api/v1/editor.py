from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.commands import (
    AssignMaintainerCommand,
    RemoveMaintainerCommand,
    UpdateToolMetadataCommand,
    UpdateToolTaxonomyCommand,
)
from skriptoteket.application.catalog.queries import (
    ListMaintainersQuery,
    ListToolTaxonomyQuery,
)
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    PublishVersionCommand,
    RequestChangesCommand,
    RollbackVersionCommand,
    RunSandboxCommand,
    SaveDraftVersionCommand,
    SubmitForReviewCommand,
)
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunStatus, ToolRun, ToolVersion, VersionState
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    ListMaintainersHandlerProtocol,
    ListToolTaxonomyHandlerProtocol,
    RemoveMaintainerHandlerProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    RunSandboxHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_contributor_api,
    require_csrf_token,
    require_superuser_api,
)
from skriptoteket.web.editor_support import (
    DEFAULT_ENTRYPOINT,
    STARTER_TEMPLATE,
    require_tool_access,
    select_default_version,
    visible_versions_for_actor,
)
from skriptoteket.web.toasts import set_toast_cookie
from skriptoteket.web.uploads import read_upload_files

router = APIRouter(prefix="/api/v1/editor", tags=["editor"])

EditorSaveMode = Literal["snapshot", "create_draft"]


class EditorToolSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None
    is_published: bool
    active_version_id: UUID | None


class EditorVersionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    version_number: int
    state: VersionState
    created_at: datetime


class EditorBootResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: EditorToolSummary
    versions: list[EditorVersionSummary]
    selected_version: EditorVersionSummary | None
    save_mode: EditorSaveMode
    derived_from_version_id: UUID | None
    entrypoint: str
    source_code: str


class CreateDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = DEFAULT_ENTRYPOINT
    source_code: str
    change_summary: str | None = None
    derived_from_version_id: UUID | None = None


class SaveDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = DEFAULT_ENTRYPOINT
    source_code: str
    change_summary: str | None = None
    expected_parent_version_id: UUID


class SaveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    redirect_url: str


class WorkflowActionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    redirect_url: str


class SubmitReviewRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    review_note: str | None = None


class PublishVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_summary: str | None = None


class RequestChangesRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: str | None = None


class SandboxRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    status: RunStatus
    started_at: datetime


class ArtifactEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    path: str
    bytes: int
    download_url: str


class EditorRunDetails(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    version_id: UUID | None
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None
    ui_payload: dict | None
    artifacts: list[ArtifactEntry]


class ToolTaxonomyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    profession_ids: list[UUID]
    category_ids: list[UUID]


class ToolTaxonomyRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    profession_ids: list[UUID]
    category_ids: list[UUID]


class EditorToolMetadataResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None


class EditorToolMetadataRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    summary: str | None = None


class MaintainerSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    email: str
    role: Role


class MaintainerListResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    maintainers: list[MaintainerSummary]


class AssignMaintainerRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str


def _to_tool_summary(tool: Tool) -> EditorToolSummary:
    return EditorToolSummary(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
        is_published=tool.is_published,
        active_version_id=tool.active_version_id,
    )


def _to_version_summary(version: ToolVersion) -> EditorVersionSummary:
    return EditorVersionSummary(
        id=version.id,
        version_number=version.version_number,
        state=version.state,
        created_at=version.created_at,
    )


def _resolve_editor_state(
    selected_version: ToolVersion | None,
) -> tuple[str, str, EditorSaveMode, UUID | None]:
    if selected_version is None:
        return DEFAULT_ENTRYPOINT, STARTER_TEMPLATE, "create_draft", None

    is_draft = selected_version.state is VersionState.DRAFT
    save_mode: EditorSaveMode = "snapshot" if is_draft else "create_draft"
    derived_from_version_id = None if is_draft else selected_version.id
    return (
        selected_version.entrypoint,
        selected_version.source_code,
        save_mode,
        derived_from_version_id,
    )


def _build_editor_response(
    *,
    tool: Tool,
    visible_versions: list[ToolVersion],
    selected_version: ToolVersion | None,
) -> EditorBootResponse:
    entrypoint, source_code, save_mode, derived_from_version_id = _resolve_editor_state(
        selected_version
    )

    return EditorBootResponse(
        tool=_to_tool_summary(tool),
        versions=[_to_version_summary(v) for v in visible_versions],
        selected_version=_to_version_summary(selected_version) if selected_version else None,
        save_mode=save_mode,
        derived_from_version_id=derived_from_version_id,
        entrypoint=entrypoint,
        source_code=source_code,
    )


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


def _build_run_details(run: ToolRun) -> EditorRunDetails:
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

    return EditorRunDetails(
        run_id=run.id,
        version_id=run.version_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_summary=run.error_summary,
        ui_payload=ui_payload,
        artifacts=artifacts,
    )


def _to_maintainer_summary(user: User) -> MaintainerSummary:
    return MaintainerSummary(
        id=user.id,
        email=user.email,
        role=user.role,
    )


@router.get("/tools/{tool_id}", response_model=EditorBootResponse)
@inject
async def get_editor_for_tool(
    tool_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor_api),
) -> EditorBootResponse:
    tool = await tools.get_by_id(tool_id=tool_id)
    if tool is None:
        raise not_found("Tool", str(tool_id))

    is_tool_maintainer = await require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )
    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    visible_versions = visible_versions_for_actor(
        actor=user,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    selected_version = select_default_version(
        actor=user,
        tool=tool,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    return _build_editor_response(
        tool=tool,
        visible_versions=visible_versions,
        selected_version=selected_version,
    )


@router.get("/tool-versions/{version_id}", response_model=EditorBootResponse)
@inject
async def get_editor_for_version(
    version_id: UUID,
    tools: FromDishka[ToolRepositoryProtocol],
    maintainers: FromDishka[ToolMaintainerRepositoryProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    user: User = Depends(require_contributor_api),
) -> EditorBootResponse:
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    tool = await tools.get_by_id(tool_id=version.tool_id)
    if tool is None:
        raise not_found("Tool", str(version.tool_id))

    is_tool_maintainer = await require_tool_access(
        actor=user,
        tool_id=tool.id,
        maintainers=maintainers,
    )
    versions = await versions_repo.list_for_tool(tool_id=tool.id, limit=50)
    visible_versions = visible_versions_for_actor(
        actor=user,
        versions=versions,
        is_tool_maintainer=is_tool_maintainer,
    )
    if not any(v.id == version.id for v in visible_versions):
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="Insufficient permissions",
            details={"tool_id": str(tool.id), "version_id": str(version.id)},
        )

    return _build_editor_response(
        tool=tool,
        visible_versions=visible_versions,
        selected_version=version,
    )


@router.get("/tools/{tool_id}/taxonomy", response_model=ToolTaxonomyResponse)
@inject
async def get_tool_taxonomy(
    tool_id: UUID,
    handler: FromDishka[ListToolTaxonomyHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> ToolTaxonomyResponse:
    result = await handler.handle(
        actor=user,
        query=ListToolTaxonomyQuery(tool_id=tool_id),
    )
    return ToolTaxonomyResponse(
        tool_id=result.tool_id,
        profession_ids=result.profession_ids,
        category_ids=result.category_ids,
    )


@router.patch("/tools/{tool_id}/taxonomy", response_model=ToolTaxonomyResponse)
@inject
async def update_tool_taxonomy(
    tool_id: UUID,
    payload: ToolTaxonomyRequest,
    handler: FromDishka[UpdateToolTaxonomyHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> ToolTaxonomyResponse:
    result = await handler.handle(
        actor=user,
        command=UpdateToolTaxonomyCommand(
            tool_id=tool_id,
            profession_ids=payload.profession_ids,
            category_ids=payload.category_ids,
        ),
    )
    return ToolTaxonomyResponse(
        tool_id=result.tool_id,
        profession_ids=result.profession_ids,
        category_ids=result.category_ids,
    )


@router.patch("/tools/{tool_id}/metadata", response_model=EditorToolMetadataResponse)
@inject
async def update_tool_metadata(
    tool_id: UUID,
    payload: EditorToolMetadataRequest,
    tools: FromDishka[ToolRepositoryProtocol],
    handler: FromDishka[UpdateToolMetadataHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> EditorToolMetadataResponse:
    summary = payload.summary
    if "summary" not in payload.model_fields_set:
        tool = await tools.get_by_id(tool_id=tool_id)
        if tool is None:
            raise not_found("Tool", str(tool_id))
        summary = tool.summary

    result = await handler.handle(
        actor=user,
        command=UpdateToolMetadataCommand(
            tool_id=tool_id,
            title=payload.title,
            summary=summary,
        ),
    )
    tool = result.tool
    return EditorToolMetadataResponse(
        id=tool.id,
        slug=tool.slug,
        title=tool.title,
        summary=tool.summary,
    )


@router.get("/tools/{tool_id}/maintainers", response_model=MaintainerListResponse)
@inject
async def list_tool_maintainers(
    tool_id: UUID,
    handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> MaintainerListResponse:
    result = await handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )


@router.post("/tools/{tool_id}/maintainers", response_model=MaintainerListResponse)
@inject
async def assign_tool_maintainer(
    tool_id: UUID,
    payload: AssignMaintainerRequest,
    handler: FromDishka[AssignMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    users: FromDishka[UserRepositoryProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> MaintainerListResponse:
    email = payload.email.strip()
    if not email:
        raise validation_error("E-post krävs.", details={"email": payload.email})

    user_auth = await users.get_auth_by_email(email=email)
    if user_auth is None:
        raise validation_error(
            f"Ingen användare med e-post: {email}",
            details={"email": email},
        )

    await handler.handle(
        actor=user,
        command=AssignMaintainerCommand(
            tool_id=tool_id,
            user_id=user_auth.user.id,
        ),
    )
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )


@router.delete("/tools/{tool_id}/maintainers/{user_id}", response_model=MaintainerListResponse)
@inject
async def remove_tool_maintainer(
    tool_id: UUID,
    user_id: UUID,
    handler: FromDishka[RemoveMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> MaintainerListResponse:
    await handler.handle(
        actor=user,
        command=RemoveMaintainerCommand(
            tool_id=tool_id,
            user_id=user_id,
        ),
    )
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )


@router.post("/tools/{tool_id}/draft", response_model=SaveResult)
@inject
async def create_draft_version(
    tool_id: UUID,
    payload: CreateDraftVersionRequest,
    response: Response,
    handler: FromDishka[CreateDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SaveResult:
    result = await handler.handle(
        actor=user,
        command=CreateDraftVersionCommand(
            tool_id=tool_id,
            derived_from_version_id=payload.derived_from_version_id,
            entrypoint=payload.entrypoint,
            source_code=payload.source_code,
            change_summary=payload.change_summary,
        ),
    )
    set_toast_cookie(response=response, message="Utkast skapat.", toast_type="success")
    return SaveResult(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )


@router.post("/tool-versions/{version_id}/save", response_model=SaveResult)
@inject
async def save_draft_version(
    version_id: UUID,
    payload: SaveDraftVersionRequest,
    response: Response,
    handler: FromDishka[SaveDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SaveResult:
    result = await handler.handle(
        actor=user,
        command=SaveDraftVersionCommand(
            version_id=version_id,
            expected_parent_version_id=payload.expected_parent_version_id,
            entrypoint=payload.entrypoint,
            source_code=payload.source_code,
            change_summary=payload.change_summary,
        ),
    )
    set_toast_cookie(response=response, message="Sparat.", toast_type="success")
    return SaveResult(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )


@router.post("/tool-versions/{version_id}/submit-review", response_model=WorkflowActionResponse)
@inject
async def submit_review(
    version_id: UUID,
    payload: SubmitReviewRequest,
    response: Response,
    handler: FromDishka[SubmitForReviewHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=SubmitForReviewCommand(
            version_id=version_id,
            review_note=payload.review_note,
        ),
    )
    set_toast_cookie(response=response, message="Skickat för granskning.", toast_type="success")
    return WorkflowActionResponse(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )


@router.post("/tool-versions/{version_id}/publish", response_model=WorkflowActionResponse)
@inject
async def publish_version(
    version_id: UUID,
    payload: PublishVersionRequest,
    response: Response,
    handler: FromDishka[PublishVersionHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=PublishVersionCommand(
            version_id=version_id,
            change_summary=payload.change_summary,
        ),
    )
    set_toast_cookie(response=response, message="Version publicerad.", toast_type="success")
    return WorkflowActionResponse(
        version_id=result.new_active_version.id,
        redirect_url=f"/admin/tool-versions/{result.new_active_version.id}",
    )


@router.post("/tool-versions/{version_id}/request-changes", response_model=WorkflowActionResponse)
@inject
async def request_changes(
    version_id: UUID,
    payload: RequestChangesRequest,
    response: Response,
    handler: FromDishka[RequestChangesHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=RequestChangesCommand(
            version_id=version_id,
            message=payload.message,
        ),
    )
    set_toast_cookie(response=response, message="Ändringar begärda.", toast_type="success")
    return WorkflowActionResponse(
        version_id=result.new_draft_version.id,
        redirect_url=f"/admin/tool-versions/{result.new_draft_version.id}",
    )


@router.post("/tool-versions/{version_id}/rollback", response_model=WorkflowActionResponse)
@inject
async def rollback_version(
    version_id: UUID,
    response: Response,
    handler: FromDishka[RollbackVersionHandlerProtocol],
    user: User = Depends(require_superuser_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=RollbackVersionCommand(version_id=version_id),
    )
    new_active = result.new_active_version
    set_toast_cookie(
        response=response,
        message=f"Återställd till v{new_active.version_number}.",
        toast_type="success",
    )
    return WorkflowActionResponse(
        version_id=new_active.id,
        redirect_url=f"/admin/tool-versions/{new_active.id}",
    )


@router.post("/tool-versions/{version_id}/run-sandbox", response_model=SandboxRunResponse)
@inject
async def run_sandbox(
    version_id: UUID,
    handler: FromDishka[RunSandboxHandlerProtocol],
    versions_repo: FromDishka[ToolVersionRepositoryProtocol],
    settings: FromDishka[Settings],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
    files: list[UploadFile] = File(...),
) -> SandboxRunResponse:
    version = await versions_repo.get_by_id(version_id=version_id)
    if version is None:
        raise not_found("ToolVersion", str(version_id))

    input_files = await read_upload_files(
        files=files,
        max_files=settings.UPLOAD_MAX_FILES,
        max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
        max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
    )
    result = await handler.handle(
        actor=user,
        command=RunSandboxCommand(
            tool_id=version.tool_id,
            version_id=version_id,
            input_files=input_files,
        ),
    )
    run = result.run
    return SandboxRunResponse(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
    )


@router.get("/tool-runs/{run_id}", response_model=EditorRunDetails)
@inject
async def get_run(
    run_id: UUID,
    runs: FromDishka[ToolRunRepositoryProtocol],
    user: User = Depends(require_contributor_api),
) -> EditorRunDetails:
    run = await _load_run_for_actor(runs=runs, run_id=run_id, actor=user)
    return _build_run_details(run)


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
