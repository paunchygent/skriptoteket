"""FastAPI dependencies for HuleEdu-derived app-local user projection.

Purpose:
    Resolve Skriptoteket-local user/profile state from verified HuleEdu Gateway
    request context without reading local browser session cookies.

Relationships:
    - Used by `GET /api/v1/profile/app-continuation`.
    - Route-scoped remediation for PR-0255; PR-0253 owns retiring or rewiring
      the remaining local-session-backed `require_user_api` role guards.
"""

from __future__ import annotations

from fastapi import Request

from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    HuleEduAppProjectionResolverProtocol,
    HuleEduInternalIdentityVerifierProtocol,
)
from skriptoteket.web.dishka_dependencies import FromDishka


async def require_huleedu_app_user_projection(
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
