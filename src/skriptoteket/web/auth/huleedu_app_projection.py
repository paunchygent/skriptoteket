"""FastAPI dependencies for HuleEdu-derived app-local authorization.

Purpose:
    Resolve Skriptoteket-local user/profile state from verified HuleEdu Gateway
    request context without reading local browser session cookies, then expose
    the app-local role guards used by browser API routes.

Relationships:
    - Used by `GET /api/v1/profile/app-continuation`.
    - Replaces the retired local-session-backed API guard family from PR-0253.
"""

from __future__ import annotations

from fastapi import Depends, Request

from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role, require_at_least_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
)
from skriptoteket.web.dishka_dependencies import FromDishka


async def require_app_user_projection_api(
    request: Request,
    verifier: FromDishka[HuleEduInternalIdentityVerifierProtocol],
    resolver: FromDishka[HuleEduAppProjectionResolverProtocol],
    clock: FromDishka[ClockProtocol],
) -> HuleEduAppUserProjection:
    """Return the local app projection proved by HuleEdu request context."""
    context = verifier.verify(
        headers=request.headers,
        now_ts=int(clock.now().timestamp()),
    )
    return await resolver.resolve(context=context)


async def require_app_user_api(
    projection: HuleEduAppUserProjection = Depends(require_app_user_projection_api),
) -> User:
    """Return the active app-local user proved by signed HuleEdu context."""
    return projection.user


async def require_app_admin_api(user: User = Depends(require_app_user_api)) -> User:
    """Return an app-local admin or superuser proved by signed HuleEdu context."""
    require_any_role(user=user, roles={Role.ADMIN, Role.SUPERUSER})
    return user


async def require_app_contributor_api(user: User = Depends(require_app_user_api)) -> User:
    """Return an app-local contributor-or-above proved by signed HuleEdu context."""
    require_at_least_role(user=user, role=Role.CONTRIBUTOR)
    return user


async def require_app_superuser_api(user: User = Depends(require_app_user_api)) -> User:
    """Return an app-local superuser proved by signed HuleEdu context."""
    require_any_role(user=user, roles={Role.SUPERUSER})
    return user
