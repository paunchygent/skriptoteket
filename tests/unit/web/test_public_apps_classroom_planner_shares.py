"""Route tests for public Klassrumskartan guest share helpers.

Purpose:
    Lock the PR-0273 route boundary for anonymous `Dela länk`: public helper
    routes parse browser snapshots, ignore ambient account authority, and
    return copyable public URLs plus browser-held revoke secrets.

Relationships:
    - Exercises direct FastAPI route callables with Dishka wrappers unwrapped.
    - Complements application handler tests for TTL, idempotency, and supersede
      behavior.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import ANY, AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    CreatePublicGuestGroupingShareHandler,
    CreatePublicGuestSeatingShareHandler,
    RevokePublicGuestShareHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.public_share_contracts import (
    PublicGuestShareResult,
    PublicGuestShareRevokeResult,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    build_share_content_hash,
    build_share_presentation_hash,
    hash_share_revoke_secret,
    hash_share_token,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.infrastructure.security.public_helper_request_throttle import (
    InMemoryPublicHelperRequestThrottle,
)
from skriptoteket.web.api.v1 import public_apps_classroom_planner_shares as api
from tests.unit.web.test_public_apps_classroom_planner_exports import (
    FixedClock,
    _registry,
    _request,
    _snapshot_payload,
    _unwrap_dishka,
)


def _artifact(*, draft_kind: PlanDraftKind) -> ClassroomPlannerShareArtifact:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token("public-token"),
        source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
        draft_kind=draft_kind,
        source_revision=4,
        guest_snapshot_fingerprint="sha256:fingerprint",
        client_operation_id="operation-123456789",
        revoke_secret_hash=hash_share_revoke_secret("r" * 32),
        title="Klass 7A",
        slug="klass-7a",
        public_path="/share/classroom/public-token/klass-7a",
        renderer_version="klassrumskartan-share-renderer-v1",
        presentation_schema_version=f"{draft_kind.value}-share-v1",
        presentation_hash=build_share_presentation_hash({"title": "Klass 7A"}),
        content_hash=build_share_content_hash(
            rendered_html="<main>Klass 7A</main>",
            rendered_css="main {}",
        ),
        presentation_payload={"title": "Klass 7A"},
        rendered_html="<main>Klass 7A</main>",
        rendered_css="main {}",
        created_at=now,
        updated_at=now,
        expires_at=datetime(2026, 6, 29, tzinfo=timezone.utc),
    )


def _payload() -> dict[str, object]:
    return {
        "snapshot": _snapshot_payload(),
        "expected_revision": 4,
        "client_operation_id": "operation-123456789",
        "revoke_secret": "r" * 32,
        "previous_public_path": "/share/classroom/old-token/klass-7a",
        "previous_revoke_secret": "p" * 32,
    }


def test_public_guest_revoke_openapi_exports_request_body() -> None:
    app = FastAPI()
    app.include_router(api.router)

    schema = app.openapi()
    operation = schema["paths"]["/api/v1/public/apps/classroom.group-seating-studio/share/revoke"][
        "post"
    ]
    request_body = operation["requestBody"]
    request_schema = request_body["content"]["application/json"]["schema"]

    assert request_body["required"] is True
    assert set(request_schema["required"]) == {"public_path", "revoke_secret"}
    assert request_schema["properties"]["public_path"]["type"] == "string"
    assert request_schema["properties"]["revoke_secret"]["minLength"] == 32


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_grouping_share_returns_public_url_and_revoke_secret() -> None:
    handler = AsyncMock(spec=CreatePublicGuestGroupingShareHandler)
    handler.handle.return_value = PublicGuestShareResult(
        artifact=_artifact(draft_kind=PlanDraftKind.GROUPING),
        public_path="/share/classroom/public-token/klass-7a",
        public_revoke_secret="r" * 32,
        superseded_previous=True,
    )

    result = await _unwrap_dishka(api.create_public_guest_grouping_share)(
        request=_request(_payload()),
        registry=_registry(),
        settings=Settings(PUBLIC_APP_BASE_URL="https://skriptoteket.hule.education"),
        clock=FixedClock(datetime(2026, 4, 30, 10, 0, 0)),
        throttle=InMemoryPublicHelperRequestThrottle(),
        handler=handler,
    )

    handler.handle.assert_awaited_once_with(request=ANY)
    request_arg = handler.handle.await_args.kwargs["request"]
    assert request_arg.client_operation_id == "operation-123456789"
    assert request_arg.previous_public_path == "/share/classroom/old-token/klass-7a"
    assert result.public_url == (
        "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a"
    )
    assert result.public_revoke_secret == "r" * 32
    assert result.superseded_previous is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_seating_share_uses_seating_handler() -> None:
    handler = AsyncMock(spec=CreatePublicGuestSeatingShareHandler)
    handler.handle.return_value = PublicGuestShareResult(
        artifact=_artifact(draft_kind=PlanDraftKind.SEATING),
        public_path="/share/classroom/public-token/klass-7a",
        public_revoke_secret="r" * 32,
        superseded_previous=False,
    )

    result = await _unwrap_dishka(api.create_public_guest_seating_share)(
        request=_request({**_payload(), "expected_revision": 2}),
        registry=_registry(),
        settings=Settings(PUBLIC_APP_BASE_URL="https://skriptoteket.hule.education"),
        clock=FixedClock(datetime(2026, 4, 30, 10, 0, 0)),
        throttle=InMemoryPublicHelperRequestThrottle(),
        handler=handler,
    )

    handler.handle.assert_awaited_once_with(request=ANY)
    assert handler.handle.await_args.kwargs["request"].expected_revision == 2
    assert result.artifact.draft_kind is PlanDraftKind.SEATING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_public_guest_revoke_returns_revoked_artifact_and_ignores_ambient_cookies() -> None:
    handler = AsyncMock(spec=RevokePublicGuestShareHandler)
    handler.handle.return_value = PublicGuestShareRevokeResult(
        artifact=_artifact(draft_kind=PlanDraftKind.SEATING).model_copy(
            update={"revoked_at": datetime(2026, 4, 30, 10, 5, 0, tzinfo=timezone.utc)}
        ),
        public_path="/share/classroom/public-token/klass-7a",
    )

    request = _request(
        {
            "public_path": "/share/classroom/public-token/klass-7a",
            "revoke_secret": "r" * 32,
        }
    )
    request.scope["headers"] = [(b"cookie", b"ambient_authority=ignored")]
    result = await _unwrap_dishka(api.revoke_public_guest_share)(
        request=request,
        registry=_registry(),
        settings=Settings(PUBLIC_APP_BASE_URL="https://skriptoteket.hule.education"),
        clock=FixedClock(datetime(2026, 4, 30, 10, 0, 0)),
        throttle=InMemoryPublicHelperRequestThrottle(),
        handler=handler,
    )

    handler.handle.assert_awaited_once_with(request=ANY)
    request_arg = handler.handle.await_args.kwargs["request"]
    assert request_arg.public_path == "/share/classroom/public-token/klass-7a"
    assert request_arg.revoke_secret == "r" * 32
    assert result.artifact.revoked_at is not None
    assert result.public_url == (
        "https://skriptoteket.hule.education/share/classroom/public-token/klass-7a"
    )
