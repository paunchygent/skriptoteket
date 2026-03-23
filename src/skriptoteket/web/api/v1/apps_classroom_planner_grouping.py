"""Grouping-specific classroom-planner endpoints.

This router holds focused grouping lifecycle endpoints so the shared classroom
planner API module does not keep growing. It exposes grouping-only transitions
that the SPA uses once the teacher has already entered the grouping workspace.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from skriptoteket.application.curated_apps.classroom_planner import (
    ActivateGroupingHistoryDraftHandler,
    CreateGroupingDraftHandler,
    DeleteHistoricGroupingDraftHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import (
    PlanDraftDto,
    serialize_plan_draft,
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
