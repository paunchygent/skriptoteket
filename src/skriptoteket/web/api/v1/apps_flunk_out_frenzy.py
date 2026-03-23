"""HTTP routes for the Flunk-Out Frenzy curated app.

This router exposes the bespoke app-specific bootstrap contract used by the SPA
shell. It keeps access checks in the web layer and delegates payload building
to the application handler.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from skriptoteket.application.curated_apps.flunk_out_frenzy import FlunkOutFrenzyBootstrapResult
from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.flunk_out_frenzy import FlunkOutFrenzyBootstrapHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

APP_ID = "games.flunk_out_frenzy"

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps", "flunk-out-frenzy"])


def _require_app_access(
    *, registry: CuratedAppRegistryProtocol, user: User
) -> CuratedAppDefinition:
    app = registry.get_by_app_id(app_id=APP_ID)
    if app is None:
        raise not_found("CuratedApp", APP_ID)
    require_at_least_role(user=user, role=app.min_role)
    return app


@router.get("/bootstrap", response_model=FlunkOutFrenzyBootstrapResult)
@inject
async def get_bootstrap(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[FlunkOutFrenzyBootstrapHandlerProtocol],
    user: User = Depends(require_user_api),
) -> FlunkOutFrenzyBootstrapResult:
    app = _require_app_access(registry=registry, user=user)
    return await handler.handle(app=app)
