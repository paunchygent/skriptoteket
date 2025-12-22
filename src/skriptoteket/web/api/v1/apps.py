"""Curated apps API endpoints for SPA deep links (ST-11-09)."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1/apps", tags=["apps"])


class AppDetailResponse(BaseModel):
    """Response payload for a curated app detail lookup."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    tool_id: UUID
    title: str
    summary: str | None
    min_role: Role


@router.get("/{app_id}", response_model=AppDetailResponse)
@inject
async def get_app_by_id(
    app_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_user_api),
) -> AppDetailResponse:
    app = registry.get_by_app_id(app_id=app_id)
    if app is None:
        raise not_found("CuratedApp", app_id)

    require_at_least_role(user=user, role=app.min_role)

    return AppDetailResponse(
        app_id=app.app_id,
        tool_id=app.tool_id,
        title=app.title,
        summary=app.summary,
        min_role=app.min_role,
    )
