"""Public curated-app bootstrap routes for dedicated guest entry hosts.

Purpose:
    Expose a public-safe curated-app bootstrap contract under
    `/api/v1/public/apps/{app_id}` without weakening the existing authenticated
    `/api/v1/apps/{app_id}` seam.

Relationships:
    - Reads the canonical `public_access_profile` from the curated-app registry.
    - Returns only public-safe metadata needed by the dedicated public SPA host.
    - Intentionally ignores ambient session cookies and owner-scoped authority.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.models import (
    CuratedAppPublicAccessProfile,
    CuratedAppUiMode,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.public_apps_support import require_public_curated_app
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1/public/apps", tags=["public-apps"])


class PublicAppBootstrapResponse(BaseModel):
    """Public-safe bootstrap payload for a curated app public host."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str | None
    ui_mode: CuratedAppUiMode
    public_access_profile: CuratedAppPublicAccessProfile
    host_mode: Literal["public"] = "public"


@router.get("/{app_id}", response_model=PublicAppBootstrapResponse)
async def get_public_app_bootstrap(
    app_id: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
) -> PublicAppBootstrapResponse:
    app = require_public_curated_app(app_id=app_id, registry=registry)

    return PublicAppBootstrapResponse(
        app_id=app.app_id,
        title=app.title,
        summary=app.summary,
        ui_mode=app.ui_mode,
        public_access_profile=app.public_access_profile,
    )
