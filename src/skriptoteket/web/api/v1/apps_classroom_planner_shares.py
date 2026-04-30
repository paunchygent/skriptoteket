"""Common authenticated Klassrumskartan share endpoints.

Purpose:
    Hold share operations that are not grouping- or seating-specific while
    keeping public token reads outside owner-scoped app APIs.

Relationships:
    - Uses application share handlers from the classroom-planner module.
    - Registered before the SPA fallback through `web.router`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from skriptoteket.application.curated_apps.classroom_planner import (
    RevokeClassroomPlannerShareArtifactHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1.apps_classroom_planner_share_contracts import (
    ClassroomPlannerShareArtifactDto,
    serialize_share_artifact,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix="/api/v1/apps/classroom.group-seating-studio",
    tags=["apps", "classroom-planner"],
)


@router.post(
    "/shares/{share_id}/revoke",
    response_model=ClassroomPlannerShareArtifactDto,
)
async def revoke_classroom_planner_share(
    share_id: UUID,
    request: Request,
    handler: FromDishka[RevokeClassroomPlannerShareArtifactHandler],
    user: User = Depends(require_app_user_api),
) -> ClassroomPlannerShareArtifactDto:
    artifact = await handler.handle(share_id=share_id, owner_user_id=user.id)
    return serialize_share_artifact(
        artifact,
        public_app_base_url=_public_app_base_url(request),
    )


def _public_app_base_url(request: Request) -> str:
    return str(getattr(request.app.state, "public_app_base_url", ""))
