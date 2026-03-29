"""Grouping-specific classroom-planner endpoints.

This router holds focused grouping lifecycle endpoints so the shared classroom
planner API module does not keep growing. It exposes grouping-only transitions
that the SPA uses once the teacher has already entered the grouping workspace.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner import (
    ActivateGroupingHistoryDraftHandler,
    CreateGroupingDraftHandler,
    CreateGroupingExportJobHandler,
    DeleteHistoricGroupingDraftHandler,
    DownloadGroupingExportJobHandler,
    GetGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
    PrepareGroupingExportHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import (
    PlanDraftDto,
    serialize_plan_draft,
)
from skriptoteket.web.api.v1.apps_classroom_planner_export_contracts import (
    PreparedGroupingExportDto,
    PrepareGroupingExportRequest,
    serialize_prepared_grouping_export,
)
from skriptoteket.web.api.v1.apps_classroom_planner_export_job_contracts import (
    CreateGroupingExportJobRequest,
    GroupingExportJobDto,
    serialize_grouping_export_job,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


class CreateGroupingDraftRequest(BaseModel):
    """Deserialize an explicit blank grouping-draft request."""

    roster_id: UUID
    template_id: UUID | None = None


@router.post("/drafts/grouping/new", response_model=PlanDraftDto)
@inject
async def create_grouping_draft(
    request: CreateGroupingDraftRequest,
    handler: FromDishka[CreateGroupingDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        template_id=request.template_id,
    )
    return serialize_plan_draft(draft)


@router.post("/drafts/grouping/{draft_id}/activate", response_model=PlanDraftDto)
@inject
async def activate_grouping_history_draft(
    draft_id: UUID,
    handler: FromDishka[ActivateGroupingHistoryDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return serialize_plan_draft(draft)


@router.delete("/drafts/grouping/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_historic_grouping_draft(
    draft_id: UUID,
    handler: FromDishka[DeleteHistoricGroupingDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(draft_id=draft_id, owner_user_id=user.id)


@router.post("/drafts/grouping/{draft_id}/exports", response_model=PreparedGroupingExportDto)
@inject
async def prepare_grouping_export(
    draft_id: UUID,
    request: PrepareGroupingExportRequest,
    handler: FromDishka[PrepareGroupingExportHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PreparedGroupingExportDto:
    prepared_export = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        export_kind=request.export_kind,
        paper_size=request.paper_size,
    )
    return serialize_prepared_grouping_export(prepared_export)


@router.post("/drafts/grouping/{draft_id}/exports/jobs", response_model=GroupingExportJobDto)
@inject
async def create_grouping_export_job(
    draft_id: UUID,
    _request: Request,
    payload: CreateGroupingExportJobRequest,
    handler: FromDishka[CreateGroupingExportJobHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> GroupingExportJobDto:
    result = await handler.handle(
        actor=user,
        draft_id=draft_id,
        export_kind=payload.export_kind,
        paper_size=payload.paper_size,
    )
    return serialize_grouping_export_job(result)


@router.get(
    "/drafts/grouping/{draft_id}/exports/jobs/recover",
    response_model=GroupingExportJobDto | None,
)
@inject
async def get_recoverable_grouping_export_job_for_draft(
    draft_id: UUID,
    handler: FromDishka[GetRecoverableGroupingExportJobForDraftHandler],
    user: User = Depends(require_user_api),
) -> GroupingExportJobDto | None:
    result = await handler.handle(
        actor=user,
        draft_id=draft_id,
    )
    return serialize_grouping_export_job(result) if result is not None else None


@router.get("/grouping/exports/jobs/{job_id}", response_model=GroupingExportJobDto)
@inject
async def get_grouping_export_job(
    job_id: UUID,
    handler: FromDishka[GetGroupingExportJobHandler],
    user: User = Depends(require_user_api),
) -> GroupingExportJobDto:
    result = await handler.handle(
        actor=user,
        job_id=job_id,
    )
    return serialize_grouping_export_job(result)


@router.get("/grouping/exports/jobs/{job_id}/download")
@inject
async def download_grouping_export_job(
    job_id: UUID,
    handler: FromDishka[DownloadGroupingExportJobHandler],
    user: User = Depends(require_user_api),
) -> Response:
    filename, media_type, content = await handler.handle(actor=user, job_id=job_id)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
