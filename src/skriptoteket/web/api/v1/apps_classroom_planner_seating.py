"""Seating-specific classroom-planner endpoints.

This router holds focused seating lifecycle endpoints so the shared classroom
planner API module does not keep growing. It exposes seating-only transitions
that the SPA uses once the teacher has already entered the seating workspace,
including the explicit seating export contract for artifact preparation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner import (
    ActivateSeatingHistoryDraftHandler,
    CreateSeatingDraftHandler,
    CreateSeatingExportJobHandler,
    DeleteHistoricSeatingDraftHandler,
    DownloadSeatingExportJobHandler,
    GetSeatingExportJobHandler,
    PrepareSeatingExportHandler,
)
from skriptoteket.domain.identity.models import User
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
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject
from skriptoteket.web.request_metadata import get_correlation_id

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


class CreateSeatingDraftRequest(BaseModel):
    """Deserialize an explicit room-bound seating-draft request."""

    roster_id: UUID
    template_id: UUID


@router.post("/drafts/seating/new", response_model=PlanDraftDto)
@inject
async def create_seating_draft(
    request: CreateSeatingDraftRequest,
    handler: FromDishka[CreateSeatingDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(
        owner_user_id=user.id,
        roster_id=request.roster_id,
        template_id=request.template_id,
    )
    return serialize_plan_draft(draft)


@router.post("/drafts/seating/{draft_id}/activate", response_model=PlanDraftDto)
@inject
async def activate_seating_history_draft(
    draft_id: UUID,
    handler: FromDishka[ActivateSeatingHistoryDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PlanDraftDto:
    draft = await handler.handle(draft_id=draft_id, owner_user_id=user.id)
    return serialize_plan_draft(draft)


@router.delete("/drafts/seating/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_historic_seating_draft(
    draft_id: UUID,
    handler: FromDishka[DeleteHistoricSeatingDraftHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> None:
    await handler.handle(draft_id=draft_id, owner_user_id=user.id)


@router.post("/drafts/seating/{draft_id}/exports", response_model=PreparedSeatingExportDto)
@inject
async def prepare_seating_export(
    draft_id: UUID,
    request: PrepareSeatingExportRequest,
    handler: FromDishka[PrepareSeatingExportHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> PreparedSeatingExportDto:
    prepared_export = await handler.handle(
        draft_id=draft_id,
        owner_user_id=user.id,
        export_kind=request.export_kind,
        layout_id=request.layout_id,
    )
    return serialize_prepared_seating_export(prepared_export)


@router.post("/drafts/seating/{draft_id}/exports/jobs", response_model=SeatingExportJobDto)
@inject
async def create_seating_export_job(
    draft_id: UUID,
    request: Request,
    payload: CreateSeatingExportJobRequest,
    handler: FromDishka[CreateSeatingExportJobHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
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


@router.get("/exports/jobs/{job_id}", response_model=SeatingExportJobDto)
@inject
async def get_seating_export_job(
    job_id: UUID,
    request: Request,
    handler: FromDishka[GetSeatingExportJobHandler],
    user: User = Depends(require_user_api),
) -> SeatingExportJobDto:
    correlation_id_uuid = get_correlation_id(request)
    result = await handler.handle(
        actor=user,
        job_id=job_id,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return serialize_seating_export_job(result)


@router.get("/exports/jobs/{job_id}/download")
@inject
async def download_seating_export_job(
    job_id: UUID,
    handler: FromDishka[DownloadSeatingExportJobHandler],
    user: User = Depends(require_user_api),
) -> Response:
    filename, content = await handler.handle(actor=user, job_id=job_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
