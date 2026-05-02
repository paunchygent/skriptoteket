"""Unit tests for public Klassrumskartan share read pages.

Purpose:
    Prove anonymous share reads resolve only by public token, avoid SPA fallback
    behavior, and always return noindex/no-store responses for active and
    unavailable shares.

Relationships:
    - Exercises `classroom_planner_share_pages.read_classroom_planner_share`.
    - Complements repository tests that prove token hashes are used in storage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
    GetClassroomPlannerShareArtifactByTokenHandler,
    GetClassroomPlannerSharePreviewAssetHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerSharePdfRendererProtocol,
)
from skriptoteket.web.routes import classroom_planner_share_pages as pages


def _unwrap_dishka(fn):
    """Extract the original function from Dishka-wrapped handlers."""

    return getattr(fn, "__dishka_orig_func__", fn)


def _artifact(**updates) -> ClassroomPlannerShareArtifact:
    now = datetime.now(timezone.utc)
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash="sha256:stored-only",
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.GROUPING,
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        source_revision=9,
        title="Klass 7A",
        slug="klass-7a",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_hash="sha256:presentation",
        content_hash="sha256:content",
        presentation_payload={"title": "Klass 7A"},
        rendered_html=(
            "<!doctype html><html><head><title>Klass 7A</title></head>"
            "<body><main>Klass 7A</main></body></html>"
        ),
        rendered_css="body { color: black; }",
        created_at=now,
        updated_at=now,
    ).model_copy(update=updates)


def _preview_asset(
    artifact: ClassroomPlannerShareArtifact,
    **updates,
) -> ClassroomPlannerSharePreviewAsset:
    now = datetime.now(timezone.utc)
    return ClassroomPlannerSharePreviewAsset(
        share_id=artifact.id,
        image_bytes=b"\x89PNG\r\npreview",
        preview_content_hash="sha256:preview",
        source_content_hash=artifact.content_hash,
        presentation_hash=artifact.presentation_hash,
        renderer_version=artifact.renderer_version,
        generated_at=now,
        updated_at=now,
    ).model_copy(update=updates)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_static_html_with_noindex_headers() -> None:
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    artifact = _artifact()
    handler.handle.return_value = artifact
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)
    preview_handler.handle.return_value = _preview_asset(artifact)

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="public-token",
        slug="klass-7a",
        handler=handler,
        preview_handler=preview_handler,
        settings=Settings(PUBLIC_APP_BASE_URL="https://skriptoteket.hule.education"),
    )

    handler.handle.assert_awaited_once_with(public_token="public-token")
    preview_handler.handle.assert_awaited_once_with(share_id=artifact.id)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert b"Klass 7A" in response.body
    assert b'property="og:image"' in response.body
    assert b'name="twitter:card" content="summary_large_image"' in response.body
    assert b'"@type":"CreativeWork"' in response.body
    assert b"Person" not in response.body
    assert b"groupMembership" not in response.body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_gone_for_revoked_artifact() -> None:
    now = datetime.now(timezone.utc)
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = _artifact(revoked_at=now)

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="public-token",
        handler=handler,
        preview_handler=AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler),
        settings=Settings(),
    )

    assert response.status_code == 410
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert b"inte tillg" in response.body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_gone_for_expired_artifact() -> None:
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = _artifact(
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="public-token",
        handler=handler,
        preview_handler=AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler),
        settings=Settings(),
    )

    assert response.status_code == 410
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_not_found_for_unknown_token() -> None:
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.side_effect = DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Missing share.",
    )

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="missing-token",
        handler=handler,
        preview_handler=AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler),
        settings=Settings(),
    )

    assert response.status_code == 404
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_preview_image_returns_png_for_active_matching_asset() -> None:
    artifact = _artifact()
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = artifact
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)
    preview_handler.handle.return_value = _preview_asset(artifact)

    response = await _unwrap_dishka(pages.read_classroom_planner_share_preview_image)(
        public_token="public-token",
        handler=handler,
        preview_handler=preview_handler,
        v="sha256:preview",
    )

    assert response.status_code == 200
    assert response.media_type == "image/png"
    assert response.body == b"\x89PNG\r\npreview"
    assert response.headers["cache-control"] == "public, max-age=86400, immutable"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_preview_image_does_not_serve_stale_hash_url() -> None:
    artifact = _artifact()
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = artifact
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)
    preview_handler.handle.return_value = _preview_asset(artifact)

    response = await _unwrap_dishka(pages.read_classroom_planner_share_preview_image)(
        public_token="public-token",
        handler=handler,
        preview_handler=preview_handler,
        v="sha256:old-preview",
    )

    assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_preview_image_does_not_leak_revoked_thumbnail() -> None:
    artifact = _artifact(revoked_at=datetime.now(timezone.utc))
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = artifact
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)
    preview_handler.handle.return_value = _preview_asset(artifact)

    response = await _unwrap_dishka(pages.read_classroom_planner_share_preview_image)(
        public_token="public-token",
        handler=handler,
        preview_handler=preview_handler,
        v="sha256:preview",
    )

    assert response.status_code == 410
    preview_handler.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_preview_image_returns_not_found_for_missing_token() -> None:
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.side_effect = DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Missing share.",
    )
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)

    response = await _unwrap_dishka(pages.read_classroom_planner_share_preview_image)(
        public_token="missing-token",
        handler=handler,
        preview_handler=preview_handler,
        v="sha256:preview",
    )

    assert response.status_code == 404
    preview_handler.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_preview_image_does_not_leak_expired_thumbnail() -> None:
    artifact = _artifact(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = artifact
    preview_handler = AsyncMock(spec=GetClassroomPlannerSharePreviewAssetHandler)
    preview_handler.handle.return_value = _preview_asset(artifact)

    response = await _unwrap_dishka(pages.read_classroom_planner_share_preview_image)(
        public_token="public-token",
        handler=handler,
        preview_handler=preview_handler,
        v="sha256:preview",
    )

    assert response.status_code == 410
    preview_handler.handle.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_pdf_download_returns_attachment_with_created_date_filename() -> None:
    created_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    artifact = _artifact(
        draft_kind=PlanDraftKind.SEATING,
        slug="klass-7a-sittschema",
        created_at=created_at,
        updated_at=created_at,
    )
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = artifact
    pdf_renderer = _FakePdfRenderer(pdf_bytes=b"%PDF-share")

    response = await _unwrap_dishka(pages.download_classroom_planner_share_pdf)(
        public_token="public-token",
        handler=handler,
        pdf_renderer=pdf_renderer,
    )

    assert response.status_code == 200
    assert response.media_type == "application/pdf"
    assert response.body == b"%PDF-share"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="klass-7a-sittschema-2026-05-01.pdf"'
    )
    assert pdf_renderer.rendered_artifact == artifact


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_pdf_download_returns_gone_for_revoked_artifact() -> None:
    now = datetime.now(timezone.utc)
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = _artifact(revoked_at=now)

    response = await _unwrap_dishka(pages.download_classroom_planner_share_pdf)(
        public_token="public-token",
        handler=handler,
        pdf_renderer=_FakePdfRenderer(),
    )

    assert response.status_code == 410
    assert response.headers["x-robots-tag"] == "noindex, nofollow"


class _FakePdfRenderer(ClassroomPlannerSharePdfRendererProtocol):
    def __init__(self, *, pdf_bytes: bytes = b"%PDF") -> None:
        self._pdf_bytes = pdf_bytes
        self.rendered_artifact: ClassroomPlannerShareArtifact | None = None

    def render(self, *, artifact: ClassroomPlannerShareArtifact) -> bytes:
        self.rendered_artifact = artifact
        return self._pdf_bytes
