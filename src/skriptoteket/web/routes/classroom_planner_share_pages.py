"""Public Klassrumskartan share artifact read route.

Purpose:
    Serve immutable share-link HTML artifacts by public token without exposing
    owner-scoped APIs, SPA shell fallback, or live draft data.

Relationships:
    - Reads artifacts through `GetClassroomPlannerShareArtifactByTokenHandler`.
    - Registered before the final SPA fallback in `web.router`.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.curated_apps.classroom_planner import (
    GetClassroomPlannerShareArtifactByTokenHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(tags=["classroom-planner-shares"])

_NOINDEX_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}


@router.get(
    "/share/classroom/{public_token}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
@router.get(
    "/share/classroom/{public_token}/{slug}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def read_classroom_planner_share(
    public_token: str,
    handler: FromDishka[GetClassroomPlannerShareArtifactByTokenHandler],
    slug: str | None = None,
) -> Response:
    try:
        artifact = await handler.handle(public_token=public_token)
    except DomainError as exc:
        if exc.code is not ErrorCode.NOT_FOUND:
            raise
        return _unavailable_response(status_code=404)

    now = datetime.now(timezone.utc)
    if artifact.revoked_at is not None:
        return _unavailable_response(status_code=410)
    if artifact.expires_at is not None and artifact.expires_at <= now:
        return _unavailable_response(status_code=410)

    return HTMLResponse(
        content=artifact.rendered_html,
        headers=_NOINDEX_HEADERS,
    )


def _unavailable_response(*, status_code: int) -> HTMLResponse:
    return HTMLResponse(
        content="\n".join(
            [
                "<!doctype html>",
                '<html lang="sv">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                '<meta name="robots" content="noindex,nofollow">',
                "<title>Delningen är inte tillgänglig</title>",
                "</head>",
                "<body>",
                "<main>",
                "<h1>Delningen är inte tillgänglig</h1>",
                "<p>Länken kan ha återkallats, gått ut eller tagits bort.</p>",
                "</main>",
                "</body>",
                "</html>",
            ]
        ),
        status_code=status_code,
        headers=_NOINDEX_HEADERS,
    )
