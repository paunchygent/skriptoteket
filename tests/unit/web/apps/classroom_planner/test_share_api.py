"""Unit coverage for authenticated Klassrumskartan share API routes.

Purpose:
    Lock the route-level PR-0274 contract: share creation uses a typed
    `expected_revision`, list routes stay draft-kind scoped, and revoke routes
    return metadata without token hashes.

Relationships:
    - Exercises direct FastAPI route callables with Dishka wrappers unwrapped.
    - Complements application handler tests that verify renderer/revision logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import Request
from starlette.types import Scope

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
    CreateAuthenticatedGroupingShareHandler,
    CreateAuthenticatedSeatingShareHandler,
    ListClassroomPlannerShareArtifactsHandler,
    RevokeClassroomPlannerShareArtifactHandler,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_grouping as grouping_api,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_seating as seating_api,
)
from skriptoteket.web.api.v1 import (
    apps_classroom_planner_shares as share_api,
)
from skriptoteket.web.api.v1.apps_classroom_planner_share_contracts import (
    CreateClassroomPlannerShareRequest,
)
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    """Extract the original function from Dishka-wrapped handlers."""

    return getattr(fn, "__dishka_orig_func__", fn)


def _http_request() -> Request:
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "scheme": "https",
        "server": ("api.hule.education", 443),
        "path": "/api/v1/apps/classroom.group-seating-studio/drafts/grouping/draft/share",
        "headers": [(b"host", b"api.hule.education")],
        "app": SimpleNamespace(
            state=SimpleNamespace(public_app_base_url="https://skriptoteket.hule.education")
        ),
    }
    return Request(scope)


def _artifact(*, draft_kind: PlanDraftKind) -> ClassroomPlannerShareArtifact:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash="sha256:stored-only",
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=draft_kind,
        owner_user_id=uuid4(),
        draft_id=uuid4(),
        roster_id=uuid4(),
        source_revision=9,
        title="Klass 7A",
        slug="klass-7a",
        public_path="/share/classroom/public-token/klass-7a",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version=f"{draft_kind.value}-share-v1",
        presentation_hash="sha256:presentation",
        content_hash="sha256:content",
        presentation_payload={"title": "Klass 7A"},
        rendered_html="<html>Klass 7A</html>",
        rendered_css="body { color: black; }",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_share_passes_expected_revision_to_handler() -> None:
    user = make_user()
    draft_id = uuid4()
    artifact = _artifact(draft_kind=PlanDraftKind.GROUPING)
    handler = AsyncMock(spec=CreateAuthenticatedGroupingShareHandler)
    handler.handle.return_value = ClassroomPlannerShareArtifactCreateResult(
        artifact=artifact,
        public_token="public-token",
    )

    result = await _unwrap_dishka(grouping_api.create_grouping_share)(
        draft_id=draft_id,
        http_request=_http_request(),
        payload=CreateClassroomPlannerShareRequest(expected_revision=9),
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=9,
    )
    assert result.artifact.id == artifact.id
    assert result.public_path == "/share/classroom/public-token/klass-7a"
    assert result.artifact.public_path == "/share/classroom/public-token/klass-7a"
    assert (
        result.artifact.public_url
        == "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a"
    )
    assert (
        result.public_url
        == "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_share_passes_expected_revision_to_handler() -> None:
    user = make_user()
    draft_id = uuid4()
    artifact = _artifact(draft_kind=PlanDraftKind.SEATING)
    handler = AsyncMock(spec=CreateAuthenticatedSeatingShareHandler)
    handler.handle.return_value = ClassroomPlannerShareArtifactCreateResult(
        artifact=artifact,
        public_token="public-token",
    )

    result = await _unwrap_dishka(seating_api.create_seating_share)(
        draft_id=draft_id,
        request=_http_request(),
        payload=CreateClassroomPlannerShareRequest(expected_revision=4),
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        expected_revision=4,
    )
    assert result.artifact.draft_kind is PlanDraftKind.SEATING
    assert result.public_url.startswith("https://skriptoteket.hule.education/share/classroom/")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_routes_scope_by_draft_kind() -> None:
    user = make_user()
    draft_id = uuid4()
    handler = AsyncMock(spec=ListClassroomPlannerShareArtifactsHandler)
    handler.handle.return_value = []

    grouping_result = await _unwrap_dishka(grouping_api.list_grouping_shares)(
        draft_id=draft_id,
        request=_http_request(),
        handler=handler,
        user=user,
    )
    seating_result = await _unwrap_dishka(seating_api.list_seating_shares)(
        draft_id=draft_id,
        request=_http_request(),
        handler=handler,
        user=user,
    )

    assert grouping_result == []
    assert seating_result == []
    assert handler.handle.await_args_list[0].kwargs["draft_kind"] is PlanDraftKind.GROUPING
    assert handler.handle.await_args_list[1].kwargs["draft_kind"] is PlanDraftKind.SEATING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revoke_share_returns_metadata_without_token_hash() -> None:
    user = make_user()
    share_id = uuid4()
    artifact = _artifact(draft_kind=PlanDraftKind.GROUPING)
    handler = AsyncMock(spec=RevokeClassroomPlannerShareArtifactHandler)
    handler.handle.return_value = artifact

    result = await _unwrap_dishka(share_api.revoke_classroom_planner_share)(
        share_id=share_id,
        request=_http_request(),
        handler=handler,
        user=user,
    )

    handler.handle.assert_awaited_once_with(share_id=share_id, owner_user_id=user.id)
    assert result.id == artifact.id
    assert not hasattr(result, "token_hash")
