"""Authenticated guest-upgrade endpoints for the Classroom Planner curated app.

This router exposes the authenticated Klassrumskartan guest-upgrade boundary
that previews or commits one browser-owned guest snapshot into owner-scoped
planner assets after a real logged-in session exists.
"""

from fastapi import APIRouter, Depends

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerGuestUpgradeHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestUpgradeReceipt,
    ClassroomPlannerGuestUpgradeRequest,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


@router.post("/guest-upgrade", response_model=ClassroomPlannerGuestUpgradeReceipt)
async def guest_upgrade(
    payload: ClassroomPlannerGuestUpgradeRequest,
    handler: FromDishka[ClassroomPlannerGuestUpgradeHandler],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> ClassroomPlannerGuestUpgradeReceipt:
    """Preview or commit one authenticated Klassrumskartan guest upgrade."""

    return await handler.handle(owner_user_id=user.id, request=payload)
