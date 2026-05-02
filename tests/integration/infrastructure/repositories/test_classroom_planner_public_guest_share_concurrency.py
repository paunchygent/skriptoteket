"""Integration tests for public guest share artifact concurrency.

Purpose:
    Prove the PostgreSQL-backed public guest share persistence operation uses
    transaction-scoped advisory locks to serialize idempotent replay,
    supersede, and active-limit enforcement across independent sessions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
    ClassroomPlannerSharePreviewAsset,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    JsonObject,
    PublicGuestSharePersistenceResult,
    build_share_content_hash,
    build_share_presentation_hash,
    build_share_preview_content_hash,
    hash_share_revoke_secret,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
)
from skriptoteket.infrastructure.repositories.classroom_planner_share_artifacts import (
    PostgreSQLClassroomPlannerShareArtifactRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


def _public_guest_artifact(
    *,
    token: str,
    client_operation_id: str,
    fingerprint: str,
    now: datetime,
    title: str,
    revoke_secret: str = "guest-revoke-secret-1234567890",
) -> ClassroomPlannerShareArtifact:
    rendered_html = f"<main>{title}</main>"
    rendered_css = "main { color: black; }"
    presentation_payload: JsonObject = {"title": title, "student_count": 2}
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token(token),
        source=ClassroomPlannerShareArtifactSource.PUBLIC_GUEST,
        draft_kind=PlanDraftKind.GROUPING,
        owner_user_id=None,
        draft_id=None,
        roster_id=None,
        template_id=None,
        source_revision=4,
        guest_snapshot_fingerprint=fingerprint,
        client_operation_id=client_operation_id,
        revoke_secret_hash=hash_share_revoke_secret(revoke_secret),
        title=title,
        slug="gastkarta",
        public_path=f"/share/classroom/{token}/gastkarta",
        preview_description="Frozen public guest grouping plan",
        renderer_version="share-renderer-v1",
        presentation_schema_version="grouping-share-v1",
        presentation_hash=build_share_presentation_hash(presentation_payload),
        content_hash=build_share_content_hash(
            rendered_html=rendered_html,
            rendered_css=rendered_css,
        ),
        presentation_payload=presentation_payload,
        rendered_html=rendered_html,
        rendered_css=rendered_css,
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(days=60),
    )


def _preview_asset(
    *,
    artifact: ClassroomPlannerShareArtifact,
    now: datetime,
) -> ClassroomPlannerSharePreviewAsset:
    image_bytes = b"\x89PNG\r\npreview"
    return ClassroomPlannerSharePreviewAsset(
        share_id=artifact.id,
        image_bytes=image_bytes,
        preview_content_hash=build_share_preview_content_hash(image_bytes),
        source_content_hash=artifact.content_hash,
        presentation_hash=artifact.presentation_hash,
        renderer_version=artifact.renderer_version,
        generated_at=now,
        updated_at=now,
    )


async def _persist_public_guest_share(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    artifact: ClassroomPlannerShareArtifact,
    now: datetime,
    max_active_per_snapshot: int = 3,
    previous_token_hash: str | None = None,
    previous_revoke_secret_hash: str | None = None,
) -> PublicGuestSharePersistenceResult:
    async with session_factory() as session:
        async with session.begin():
            repository = PostgreSQLClassroomPlannerShareArtifactRepository(session)
            return await repository.create_or_reuse_public_guest_share(
                artifact=artifact,
                preview_asset=_preview_asset(artifact=artifact, now=now),
                previous_token_hash=previous_token_hash,
                previous_revoke_secret_hash=previous_revoke_secret_hash,
                now=now,
                max_active_per_snapshot=max_active_per_snapshot,
            )


async def _list_public_guest_models(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    fingerprint: str,
) -> list[ClassroomPlannerShareArtifactModel]:
    async with session_factory() as session:
        result = await session.execute(
            select(ClassroomPlannerShareArtifactModel)
            .where(
                ClassroomPlannerShareArtifactModel.source
                == ClassroomPlannerShareArtifactSource.PUBLIC_GUEST.value,
                ClassroomPlannerShareArtifactModel.guest_snapshot_fingerprint == fingerprint,
            )
            .order_by(ClassroomPlannerShareArtifactModel.created_at)
        )
        return list(result.scalars().all())


@pytest.mark.integration
async def test_public_guest_same_client_operation_replays_with_independent_sessions(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    del db_session
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    fingerprint = "sha256:integration-same-client"
    client_operation_id = "operation-integration-same-client"

    first, second = await asyncio.gather(
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-same-client-a",
                client_operation_id=client_operation_id,
                fingerprint=fingerprint,
                now=now,
                title="Gästkarta A",
            ),
            now=now,
        ),
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-same-client-b",
                client_operation_id=client_operation_id,
                fingerprint=fingerprint,
                now=now,
                title="Gästkarta B",
            ),
            now=now,
        ),
    )

    assert first.artifact is not None
    assert second.artifact is not None
    assert first.artifact.id == second.artifact.id
    assert {first.reused_client_operation, second.reused_client_operation} == {False, True}
    rows = await _list_public_guest_models(
        session_factory=session_factory,
        fingerprint=fingerprint,
    )
    assert len(rows) == 1
    assert rows[0].client_operation_id == client_operation_id


@pytest.mark.integration
async def test_public_guest_two_tab_supersede_allows_one_newest_link(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    del db_session
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    fingerprint = "sha256:integration-two-tab-supersede"
    previous_secret = "previous-secret-value-1234567890"
    previous = await _persist_public_guest_share(
        session_factory=session_factory,
        artifact=_public_guest_artifact(
            token="public-token-previous",
            client_operation_id="operation-integration-previous",
            fingerprint=fingerprint,
            now=now,
            title="Tidigare gästkarta",
            revoke_secret=previous_secret,
        ),
        now=now,
    )
    assert previous.artifact is not None

    first, second = await asyncio.gather(
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-supersede-a",
                client_operation_id="operation-integration-supersede-a",
                fingerprint=fingerprint,
                now=now,
                title="Ny gästkarta A",
            ),
            previous_token_hash=previous.artifact.token_hash,
            previous_revoke_secret_hash=previous.artifact.revoke_secret_hash,
            now=now,
        ),
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-supersede-b",
                client_operation_id="operation-integration-supersede-b",
                fingerprint=fingerprint,
                now=now,
                title="Ny gästkarta B",
            ),
            previous_token_hash=previous.artifact.token_hash,
            previous_revoke_secret_hash=previous.artifact.revoke_secret_hash,
            now=now,
        ),
    )

    created = [result for result in (first, second) if result.artifact is not None]
    stale = [result for result in (first, second) if result.previous_already_superseded]
    assert len(created) == 1
    assert created[0].superseded_previous is True
    assert len(stale) == 1
    rows = await _list_public_guest_models(
        session_factory=session_factory,
        fingerprint=fingerprint,
    )
    previous_rows = [row for row in rows if row.id == previous.artifact.id]
    active_new_rows = [
        row for row in rows if row.id != previous.artifact.id and row.revoked_at is None
    ]
    assert len(previous_rows) == 1
    assert previous_rows[0].revoked_at == now
    assert len(active_new_rows) == 1


@pytest.mark.integration
async def test_public_guest_active_limit_holds_under_independent_sessions(
    db_session: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    del db_session
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    fingerprint = "sha256:integration-active-limit"

    first, second = await asyncio.gather(
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-limit-a",
                client_operation_id="operation-integration-limit-a",
                fingerprint=fingerprint,
                now=now,
                title="Aktiv gästkarta A",
            ),
            now=now,
            max_active_per_snapshot=1,
        ),
        _persist_public_guest_share(
            session_factory=session_factory,
            artifact=_public_guest_artifact(
                token="public-token-limit-b",
                client_operation_id="operation-integration-limit-b",
                fingerprint=fingerprint,
                now=now,
                title="Aktiv gästkarta B",
            ),
            now=now,
            max_active_per_snapshot=1,
        ),
    )

    created = [result for result in (first, second) if result.artifact is not None]
    limited = [result for result in (first, second) if result.active_limit_exceeded]
    assert len(created) == 1
    assert len(limited) == 1
    rows = await _list_public_guest_models(
        session_factory=session_factory,
        fingerprint=fingerprint,
    )
    assert len(rows) == 1
    assert rows[0].revoked_at is None
