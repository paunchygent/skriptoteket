"""Public Klassrumskartan share artifact read route.

Purpose:
    Serve immutable share-link HTML artifacts by public token without exposing
    owner-scoped APIs, SPA shell fallback, or live draft data.

Relationships:
    - Reads artifacts through `GetClassroomPlannerShareArtifactByTokenHandler`.
    - Registered before the final SPA fallback in `web.router`.
"""

import html
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote, urljoin

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerSharePreviewAsset,
    GetClassroomPlannerShareArtifactByTokenHandler,
    GetClassroomPlannerSharePreviewAssetHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    build_share_preview_image_path,
)
from skriptoteket.config import Settings
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
_PREVIEW_HEADERS = {
    "Cache-Control": "public, max-age=86400, immutable",
    "X-Robots-Tag": "noindex, nofollow",
}


@router.get(
    "/share/classroom/{public_token}/preview.png",
    response_class=Response,
    include_in_schema=False,
)
async def read_classroom_planner_share_preview_image(
    public_token: str,
    handler: FromDishka[GetClassroomPlannerShareArtifactByTokenHandler],
    preview_handler: FromDishka[GetClassroomPlannerSharePreviewAssetHandler],
    v: str | None = None,
) -> Response:
    try:
        artifact = await _load_active_artifact(public_token=public_token, handler=handler)
        preview_asset = await preview_handler.handle(share_id=artifact.id)
    except _UnavailableShareError as exc:
        return _unavailable_response(status_code=exc.status_code)
    except DomainError as exc:
        if exc.code is not ErrorCode.NOT_FOUND:
            raise
        return _unavailable_response(status_code=404)

    if not _preview_matches_artifact(preview_asset=preview_asset, artifact=artifact):
        return _unavailable_response(status_code=404)
    if v is not None and v != preview_asset.preview_content_hash:
        return _unavailable_response(status_code=404)

    return Response(
        content=preview_asset.image_bytes,
        media_type=preview_asset.content_type,
        headers={
            **_PREVIEW_HEADERS,
            "Content-Length": str(len(preview_asset.image_bytes)),
        },
    )


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
    preview_handler: FromDishka[GetClassroomPlannerSharePreviewAssetHandler],
    settings: FromDishka[Settings],
    slug: str | None = None,
) -> Response:
    del slug
    try:
        artifact = await _load_active_artifact(public_token=public_token, handler=handler)
    except _UnavailableShareError as exc:
        return _unavailable_response(status_code=exc.status_code)

    try:
        preview_asset = await preview_handler.handle(share_id=artifact.id)
    except DomainError as exc:
        if exc.code is not ErrorCode.NOT_FOUND:
            raise
        preview_asset = None

    content = artifact.rendered_html
    if preview_asset is not None and _preview_matches_artifact(
        preview_asset=preview_asset,
        artifact=artifact,
    ):
        content = _with_social_metadata(
            artifact=artifact,
            preview_asset=preview_asset,
            public_token=public_token,
            public_app_base_url=settings.PUBLIC_APP_BASE_URL,
        )

    return HTMLResponse(
        content=content,
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


def _preview_matches_artifact(
    *,
    preview_asset: ClassroomPlannerSharePreviewAsset,
    artifact: ClassroomPlannerShareArtifact,
) -> bool:
    return (
        preview_asset.source_content_hash == artifact.content_hash
        and preview_asset.presentation_hash == artifact.presentation_hash
        and preview_asset.renderer_version == artifact.renderer_version
    )


def _with_social_metadata(
    *,
    artifact: ClassroomPlannerShareArtifact,
    preview_asset: ClassroomPlannerSharePreviewAsset,
    public_token: str,
    public_app_base_url: str,
) -> str:
    public_path = artifact.public_path or f"/share/classroom/{public_token}"
    share_url = _absolute_url(public_app_base_url, public_path)
    image_path = build_share_preview_image_path(
        public_token=public_token,
        preview_content_hash=preview_asset.preview_content_hash,
    )
    image_url = _absolute_url(public_app_base_url, image_path)
    escaped_title = html.escape(artifact.title, quote=True)
    description = artifact.preview_description or "Delad Klassrumskartan-plan."
    escaped_description = html.escape(description, quote=True)
    escaped_share_url = html.escape(share_url, quote=True)
    escaped_image_url = html.escape(image_url, quote=True)
    escaped_alt = html.escape(f"Förhandsvisning av {artifact.title}", quote=True)
    json_ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CreativeWork",
            "name": artifact.title,
            "description": description,
            "url": share_url,
            "image": image_url,
            "thumbnailUrl": image_url,
            "inLanguage": "sv-SE",
            "dateCreated": artifact.created_at.isoformat(),
            "isPartOf": {"@type": "WebSite", "name": "Skriptoteket"},
            "provider": {"@type": "Organization", "name": "Skriptoteket"},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    metadata = "\n".join(
        [
            f'<meta property="og:title" content="{escaped_title}">',
            f'<meta property="og:description" content="{escaped_description}">',
            '<meta property="og:type" content="article">',
            '<meta property="og:site_name" content="Skriptoteket">',
            f'<meta property="og:url" content="{escaped_share_url}">',
            f'<meta property="og:image" content="{escaped_image_url}">',
            f'<meta property="og:image:secure_url" content="{escaped_image_url}">',
            f'<meta property="og:image:type" content="{preview_asset.content_type}">',
            f'<meta property="og:image:width" content="{preview_asset.width}">',
            f'<meta property="og:image:height" content="{preview_asset.height}">',
            f'<meta property="og:image:alt" content="{escaped_alt}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{escaped_title}">',
            f'<meta name="twitter:description" content="{escaped_description}">',
            f'<meta name="twitter:image" content="{escaped_image_url}">',
            f'<meta name="twitter:image:alt" content="{escaped_alt}">',
            '<script type="application/ld+json">',
            json_ld,
            "</script>",
        ]
    )
    return artifact.rendered_html.replace("</head>", f"{metadata}\n</head>", 1)


def _absolute_url(base_url: str, path: str) -> str:
    normalized_base = base_url.rstrip("/") + "/"
    if path.startswith(("http://", "https://")):
        return path
    quoted_path = quote(path, safe="/:?=&%#")
    return urljoin(normalized_base, quoted_path.lstrip("/"))


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
