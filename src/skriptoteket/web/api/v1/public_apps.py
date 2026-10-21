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
    CuratedAppDefinition,
    CuratedAppPublicAccessProfile,
    CuratedAppPublicCapability,
    CuratedAppPublicRuntimeStatus,
    CuratedAppUiMode,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.public_apps_support import (
    require_public_curated_app,
    require_public_curated_app_capability,
)
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1/public/apps", tags=["public-apps"])

EXAM_CONVERTER_APP_ID = "documents.conversion_hub"
EXAM_CONVERTER_SCOPE = "exam_converter"
EXAM_CONVERTER_ROUTE_SLUG = "exam-converter"
EXAM_CONVERTER_PUBLIC_FRONTEND_ROUTE = (
    f"/public/apps/{EXAM_CONVERTER_APP_ID}/{EXAM_CONVERTER_ROUTE_SLUG}"
)
EXAM_CONVERTER_PUBLIC_API_NAMESPACE = (
    f"/api/v1/public/apps/{EXAM_CONVERTER_APP_ID}/{EXAM_CONVERTER_ROUTE_SLUG}"
)

_CAPABILITY_SCOPE_BY_ROUTE_SLUG = {EXAM_CONVERTER_ROUTE_SLUG: EXAM_CONVERTER_SCOPE}


class PublicCapabilityMetadata(BaseModel):
    """Public-safe scoped capability metadata."""

    model_config = ConfigDict(frozen=True)

    scope: str
    profile: CuratedAppPublicAccessProfile
    frontend_route: str
    api_namespace: str
    runtime_status: CuratedAppPublicRuntimeStatus


class PublicAppBootstrapResponse(BaseModel):
    """Public-safe bootstrap payload for a curated app public host."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str | None
    ui_mode: CuratedAppUiMode
    public_access_profile: CuratedAppPublicAccessProfile
    host_mode: Literal["public"] = "public"


class PublicAppCapabilityBootstrapResponse(BaseModel):
    """Public-safe bootstrap payload for a scoped curated-app capability."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    title: str
    summary: str | None
    ui_mode: CuratedAppUiMode
    public_access_profile: CuratedAppPublicAccessProfile
    public_capability: PublicCapabilityMetadata
    host_mode: Literal["public"] = "public"


def _capability_scope_from_route_slug(*, route_slug: str) -> str:
    return _CAPABILITY_SCOPE_BY_ROUTE_SLUG.get(route_slug.strip(), "")


def _build_exam_converter_capability_metadata(
    *, capability: CuratedAppPublicCapability
) -> PublicCapabilityMetadata:
    return PublicCapabilityMetadata(
        scope=capability.scope,
        profile=capability.profile,
        frontend_route=EXAM_CONVERTER_PUBLIC_FRONTEND_ROUTE,
        api_namespace=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
        runtime_status=capability.runtime_status,
    )


def _build_scoped_bootstrap_response(
    *,
    app: CuratedAppDefinition,
    capability: CuratedAppPublicCapability,
) -> PublicAppCapabilityBootstrapResponse:
    if app.app_id != EXAM_CONVERTER_APP_ID or capability.scope != EXAM_CONVERTER_SCOPE:
        raise ValueError("unsupported public capability bootstrap contract")

    return PublicAppCapabilityBootstrapResponse(
        app_id=app.app_id,
        title=app.title,
        summary=app.summary,
        ui_mode=app.ui_mode,
        public_access_profile=app.public_access_profile,
        public_capability=_build_exam_converter_capability_metadata(capability=capability),
    )


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


@router.get("/{app_id}/{capability_slug}", response_model=PublicAppCapabilityBootstrapResponse)
async def get_public_app_capability_bootstrap(
    app_id: str,
    capability_slug: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
) -> PublicAppCapabilityBootstrapResponse:
    scope = _capability_scope_from_route_slug(route_slug=capability_slug)
    app, capability = require_public_curated_app_capability(
        app_id=app_id,
        scope=scope,
        registry=registry,
    )

    return _build_scoped_bootstrap_response(app=app, capability=capability)
