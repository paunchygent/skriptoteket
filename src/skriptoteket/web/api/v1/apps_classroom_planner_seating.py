"""Seating-specific classroom-planner endpoints.
This router holds focused seating lifecycle endpoints so the shared classroom
planner API module does not keep growing. It exposes seating-only transitions
that the SPA uses once the teacher has already entered the seating workspace,
including the explicit seating export contract, the backend-owned smart run,
and artifact preparation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner import (
    ActivateSeatingHistoryDraftHandler,
    CreateAuthenticatedSeatingShareHandler,
    CreateSeatingDraftHandler,
    CreateSeatingExportJobHandler,
    DeleteHistoricSeatingDraftHandler,
    DownloadSeatingExportJobHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetSeatingExportJobHandler,
    ListClassroomPlannerShareArtifactsHandler,
    PrepareSeatingExportHandler,
    RunSmartSeatingHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1.apps_classroom_planner import (
    DraftWorkspaceResponse,
    _serialize_workspace,
)
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import (
    PlanDraftDto,
    serialize_plan_draft,
)
from skriptoteket.web.api.v1.apps_classroom_planner_export_contracts import (
    PreparedSeatingExportDto,
    PrepareSeatingExportRequest,
    serialize_prepared_seating_export,
)
from skriptoteket.web.api.v1.apps_classroom_planner_export_job_contracts import (
    CreateSeatingExportJobRequest,
    SeatingExportJobDto,
    serialize_seating_export_job,
)
from skriptoteket.web.api.v1.apps_classroom_planner_share_contracts import (
    ClassroomPlannerShareArtifactDto,
    CreateClassroomPlannerShareRequest,
    CreatedClassroomPlannerShareDto,
    serialize_created_share,
    serialize_share_artifact,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_correlation_id

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


class CreateSeatingDraftRequest(BaseModel):
    """Deserialize an explicit room-bound seating-draft request."""

    roster_id: UUID
    template_id: UUID


class SmartSeatingRunRequest(BaseModel):
    """Deserialize one backend-owned seating smart-run request."""

    expected_revision: int


class AppliedSmartSeatingRunResponse(BaseModel):
    """Serialize one applied backend smart-seating result."""

    status: str
    workspace: DraftWorkspaceResponse
    used_history: bool
    message: str | None


class BlockedSmartSeatingRunResponse(BaseModel):
    """Serialize one blocked backend smart-seating result."""

    status: str
    reason: str
    message: str
    workspace: None = None
    used_history: bool


@router.post("/drafts/seating/new", response_model=PlanDraftDto)
async def create_seating_draft(
    request: CreateSeatingDraftRequest,
    handler: FromDishka[CreateSeatingDraftHandler],
    user: User = Depends(require_app_user_api),
) -> PlanDraftDto:
    draft = await handler.handle(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        template_id=request.template_id,
    )
    return serialize_plan_draft(draft)


@router.post("/drafts/seating/{draft_id}/activate", response_model=PlanDraftDto)
async def activate_seating_history_draft(
    draft_id: UUID,
    handler: FromDishka[ActivateSeatingHistoryDraftHandler],
    user: User = Depends(require_app_user_api),
) -> PlanDraftDto:
    draft = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return serialize_plan_draft(draft)


@router.delete("/drafts/seating/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_historic_seating_draft(
    draft_id: UUID,
    handler: FromDishka[DeleteHistoricSeatingDraftHandler],
    user: User = Depends(require_app_user_api),
) -> None:
    await handler.handle(draft_id=draft_id, owner_user_id=user.id)


@router.post(
    "/drafts/seating/{draft_id}/smart-run",
    response_model=AppliedSmartSeatingRunResponse | BlockedSmartSeatingRunResponse,
)
async def run_smart_seating(
    draft_id: UUID,
    request: SmartSeatingRunRequest,
    handler: FromDishka[RunSmartSeatingHandler],
    user: User = Depends(require_app_user_api),
) -> AppliedSmartSeatingRunResponse | BlockedSmartSeatingRunResponse:
    result = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=request.expected_revision,
    )
    if result.status == "blocked":
        return BlockedSmartSeatingRunResponse(
            status=result.status,
            reason=result.reason,
            message=result.message,
            used_history=result.used_history,
        )
    return AppliedSmartSeatingRunResponse(
        status=result.status,
        workspace=_serialize_workspace(result.workspace),
        used_history=result.used_history,
        message=result.message,
    )


@router.post("/drafts/seating/{draft_id}/exports", response_model=PreparedSeatingExportDto)
async def prepare_seating_export(
    draft_id: UUID,
    request: PrepareSeatingExportRequest,
    handler: FromDishka[PrepareSeatingExportHandler],
    user: User = Depends(require_app_user_api),
) -> PreparedSeatingExportDto:
    prepared_export = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        export_kind=request.export_kind,
        layout_id=request.layout_id,
    )
    return serialize_prepared_seating_export(prepared_export)


@router.post("/drafts/seating/{draft_id}/exports/jobs", response_model=SeatingExportJobDto)
async def create_seating_export_job(
    draft_id: UUID,
    request: Request,
    payload: CreateSeatingExportJobRequest,
    handler: FromDishka[CreateSeatingExportJobHandler],
    user: User = Depends(require_app_user_api),
) -> SeatingExportJobDto:
    correlation_id_uuid = get_correlation_id(request)
    result = await handler.handle(
        actor=user,
        draft_id=draft_id,
        export_kind=payload.export_kind,
        layout_id=payload.layout_id,
        paper_size=payload.paper_size,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return serialize_seating_export_job(result)


@router.post(
    "/drafts/seating/{draft_id}/share",
    response_model=CreatedClassroomPlannerShareDto,
)
async def create_seating_share(
    draft_id: UUID,
    request: Request,
    payload: CreateClassroomPlannerShareRequest,
    handler: FromDishka[CreateAuthenticatedSeatingShareHandler],
    user: User = Depends(require_app_user_api),
) -> CreatedClassroomPlannerShareDto:
    result = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=payload.expected_revision,
    )
    return serialize_created_share(
        result,
        public_app_base_url=_public_app_base_url(request),
    )


@router.get(
    "/drafts/seating/{draft_id}/shares",
    response_model=list[ClassroomPlannerShareArtifactDto],
)
async def list_seating_shares(
    draft_id: UUID,
    request: Request,
    handler: FromDishka[ListClassroomPlannerShareArtifactsHandler],
    user: User = Depends(require_app_user_api),
) -> list[ClassroomPlannerShareArtifactDto]:
    artifacts = await handler.handle(
        owner_user_id=user.id,
        draft_id=draft_id,
        draft_kind=PlanDraftKind.SEATING,
    )
    return [
        serialize_share_artifact(
            artifact,
            public_app_base_url=_public_app_base_url(request),
        )
        for artifact in artifacts
    ]


def _public_app_base_url(request: Request) -> str:
    return str(getattr(request.app.state, "public_app_base_url", ""))


@router.get(
    "/drafts/seating/{draft_id}/exports/jobs/recover",
    response_model=SeatingExportJobDto | None,
)
async def get_recoverable_seating_export_job_for_draft(
    draft_id: UUID,
    request: Request,
    handler: FromDishka[GetRecoverableSeatingExportJobForDraftHandler],
    user: User = Depends(require_app_user_api),
) -> SeatingExportJobDto | None:
    correlation_id_uuid = get_correlation_id(request)
    result = await handler.handle(
        actor=user,
        draft_id=draft_id,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return serialize_seating_export_job(result) if result is not None else None


@router.get("/exports/jobs/{job_id}", response_model=SeatingExportJobDto)
async def get_seating_export_job(
    job_id: UUID,
    request: Request,
    handler: FromDishka[GetSeatingExportJobHandler],
    user: User = Depends(require_app_user_api),
) -> SeatingExportJobDto:
    correlation_id_uuid = get_correlation_id(request)
    result = await handler.handle(
        actor=user,
        job_id=job_id,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return serialize_seating_export_job(result)


@router.get("/exports/jobs/{job_id}/download")
async def download_seating_export_job(
    job_id: UUID,
    handler: FromDishka[DownloadSeatingExportJobHandler],
    user: User = Depends(require_app_user_api),
) -> Response:
    filename, media_type, content = await handler.handle(actor=user, job_id=job_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
