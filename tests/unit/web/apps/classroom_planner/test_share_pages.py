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
    GetClassroomPlannerShareArtifactByTokenHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import DomainError, ErrorCode
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
        rendered_html="<html><body><main>Klass 7A</main></body></html>",
        rendered_css="body { color: black; }",
        created_at=now,
        updated_at=now,
    ).model_copy(update=updates)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_static_html_with_noindex_headers() -> None:
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = _artifact()

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="public-token",
        slug="klass-7a",
        handler=handler,
    )

    handler.handle.assert_awaited_once_with(public_token="public-token")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert b"Klass 7A" in response.body


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_share_read_returns_gone_for_revoked_artifact() -> None:
    now = datetime.now(timezone.utc)
    handler = AsyncMock(spec=GetClassroomPlannerShareArtifactByTokenHandler)
    handler.handle.return_value = _artifact(revoked_at=now)

    response = await _unwrap_dishka(pages.read_classroom_planner_share)(
        public_token="public-token",
        handler=handler,
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
    )

    assert response.status_code == 404
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
