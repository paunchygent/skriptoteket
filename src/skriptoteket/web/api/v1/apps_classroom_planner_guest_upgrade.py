"""Authenticated guest-upgrade endpoints for the Classroom Planner curated app.

This router exposes the authenticated Klassrumskartan guest-upgrade boundary
that previews or commits one browser-owned guest snapshot into owner-scoped
planner assets after a real logged-in session exists.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
    GetClassroomPlannerGuestUpgradeConsumptionHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


class ClassroomPlannerGuestUpgradeConsumptionStatusResponse(BaseModel):
    """Authenticated guest-upgrade consumption truth for one user/app."""

    model_config = ConfigDict(frozen=True)

    consumed: bool


@router.post("/guest-upgrade", response_model=ClassroomPlannerGuestUpgradeReceipt)
async def guest_upgrade(
    payload: ClassroomPlannerGuestUpgradeRequest,
    handler: FromDishka[ClassroomPlannerGuestUpgradeHandler],
    user: User = Depends(require_app_user_api),
) -> ClassroomPlannerGuestUpgradeReceipt:
    """Preview or commit one authenticated Klassrumskartan guest upgrade."""

    return await handler.handle(owner_user_id=user.id, request=payload)


@router.get(
    "/guest-upgrade/consumption",
    response_model=ClassroomPlannerGuestUpgradeConsumptionStatusResponse,
)
async def get_guest_upgrade_consumption_status(
    handler: FromDishka[GetClassroomPlannerGuestUpgradeConsumptionHandler],
    user: User = Depends(require_app_user_api),
) -> ClassroomPlannerGuestUpgradeConsumptionStatusResponse:
    """Return whether this user's guest-upgrade bridge was already consumed."""

    return ClassroomPlannerGuestUpgradeConsumptionStatusResponse(
        consumed=await handler.handle(owner_user_id=user.id)
    )
