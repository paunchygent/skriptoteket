"""Public Klassrumskartan share artifact read route.

Purpose:
    Serve immutable share-link HTML artifacts by public token without exposing
    owner-scoped APIs, SPA shell fallback, or live draft data.

Relationships:
    - Reads artifacts through `GetClassroomPlannerShareArtifactByTokenHandler`.
    - Registered before the final SPA fallback in `web.router`.
"""

import re
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    GetClassroomPlannerShareArtifactByTokenHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerSharePdfRendererProtocol,
)
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(tags=["classroom-planner-shares"])

_FILENAME_PART_PATTERN = re.compile(r"[^a-z0-9]+")
_NOINDEX_HEADERS = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}


@router.get(
    "/share/classroom/{public_token}/download.pdf",
    response_class=Response,
    include_in_schema=False,
)
async def download_classroom_planner_share_pdf(
    public_token: str,
    handler: FromDishka[GetClassroomPlannerShareArtifactByTokenHandler],
    pdf_renderer: FromDishka[ClassroomPlannerSharePdfRendererProtocol],
) -> Response:
    try:
        artifact = await _load_active_artifact(public_token=public_token, handler=handler)
    except _UnavailableShareError as exc:
        return _unavailable_response(status_code=exc.status_code)

    return Response(
        content=pdf_renderer.render(artifact=artifact),
        media_type="application/pdf",
        headers={
            **_NOINDEX_HEADERS,
            "Content-Disposition": f'attachment; filename="{_pdf_filename(artifact)}"',
        },
    )


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
    del slug
    try:
        artifact = await _load_active_artifact(public_token=public_token, handler=handler)
    except _UnavailableShareError as exc:
        return _unavailable_response(status_code=exc.status_code)

    return HTMLResponse(
        content=artifact.rendered_html,
        headers=_NOINDEX_HEADERS,
    )


async def _load_active_artifact(
    *,
    public_token: str,
    handler: GetClassroomPlannerShareArtifactByTokenHandler,
) -> ClassroomPlannerShareArtifact:
    """Resolve an active share artifact or raise an unavailable status."""

    try:
        artifact = await handler.handle(public_token=public_token)
    except DomainError as exc:
        if exc.code is not ErrorCode.NOT_FOUND:
            raise
        raise _UnavailableShareError(status_code=404) from exc

    now = datetime.now(timezone.utc)
    if artifact.revoked_at is not None:
        raise _UnavailableShareError(status_code=410)
    if artifact.expires_at is not None and artifact.expires_at <= now:
        raise _UnavailableShareError(status_code=410)
    return artifact


def _pdf_filename(artifact: ClassroomPlannerShareArtifact) -> str:
    """Build a stable share PDF attachment filename with creation date."""

    date_part = artifact.created_at.date().isoformat()
    title_part = _FILENAME_PART_PATTERN.sub("-", artifact.slug.casefold()).strip("-")
    stem = title_part or "klassrumskartan"
    return f"{stem}-{date_part}.pdf"


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


class _UnavailableShareError(Exception):
    """Carry the public unavailable response status for one share request."""

    def __init__(self, *, status_code: int) -> None:
        super().__init__("Share artifact is unavailable.")
        self.status_code = status_code
