"""Integration tests for the classroom-planner share artifact repository.

Purpose:
    Verify the dedicated share artifact table persists token-hash lookups,
    owner/draft listing, and revoke state without involving export-job tables.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.classroom_planner import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactSource,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    JsonObject,
    build_share_content_hash,
    build_share_presentation_hash,
    hash_share_token,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomSelectionMode,
    PlanDraftKind,
    PlanDraftStatus,
)
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import PlanDraftModel
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import RoomTemplateModel
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.infrastructure.db.models.classroom_planner_share_artifact import (
    ClassroomPlannerShareArtifactModel,
)
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.classroom_planner_share_artifacts import (
    PostgreSQLClassroomPlannerShareArtifactRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _seed_owner_and_draft(
    *,
    db_session: AsyncSession,
    now: datetime,
) -> tuple[UUID, UUID, UUID, UUID]:
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    draft_id = uuid4()
    db_session.add(
        UserModel(
            id=owner_user_id,
            email=f"share-{owner_user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        RosterModel(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[{"id": "student-1", "display_name": "Ada"}],
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        RoomTemplateModel(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal A",
            seats=[],
            fixtures=[],
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        PlanDraftModel(
            id=draft_id,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING.value,
            template_id=template_id,
            task_entry_classroom_selection_mode=ClassroomSelectionMode.OPTIONAL.value,
            status=PlanDraftStatus.ACTIVE.value,
            revision=3,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return owner_user_id, roster_id, template_id, draft_id


def _artifact(
    *,
    owner_user_id: UUID,
    roster_id: UUID,
    template_id: UUID | None = None,
    draft_id: UUID,
    now: datetime,
    title: str = "Klass 7A",
) -> ClassroomPlannerShareArtifact:
    rendered_html = f"<main>{title}</main>"
    rendered_css = "main { color: black; }"
    presentation_payload: JsonObject = {"title": title, "student_count": 1}
    return ClassroomPlannerShareArtifact(
        id=uuid4(),
        token_hash=hash_share_token(f"token-{title}"),
        source=ClassroomPlannerShareArtifactSource.AUTHENTICATED,
        draft_kind=PlanDraftKind.GROUPING,
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        roster_id=roster_id,
        template_id=template_id,
        source_revision=3,
        title=title,
        slug="klass-7a",
        public_path="/share/classroom/public-token/klass-7a",
        preview_description="Frozen grouping plan",
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
    )


@pytest.mark.integration
async def test_share_artifact_repository_create_lookup_list_and_revoke(
    db_session: AsyncSession,
) -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id, roster_id, template_id, draft_id = await _seed_owner_and_draft(
        db_session=db_session,
        now=now,
    )
    repository = PostgreSQLClassroomPlannerShareArtifactRepository(db_session)
    artifact = _artifact(
        owner_user_id=owner_user_id,
        roster_id=roster_id,
        template_id=template_id,
        draft_id=draft_id,
        now=now,
    )

    created = await repository.create(artifact=artifact)
    by_id = await repository.get_by_id(share_id=artifact.id)
    by_token = await repository.get_by_token_hash(token_hash=artifact.token_hash)
    listed = await repository.list_for_owner_draft(
        owner_user_id=owner_user_id,
        draft_id=draft_id,
        draft_kind=PlanDraftKind.GROUPING,
    )
    revoked_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    revoked = await repository.revoke_owned(
        share_id=artifact.id,
        owner_user_id=owner_user_id,
        revoked_at=revoked_at,
    )

    assert created == artifact
    assert by_id == artifact
    assert by_token == artifact
    assert listed == [artifact]
    assert revoked is not None
    assert revoked.revoked_at == revoked_at
    assert (
        await repository.revoke_owned(
            share_id=artifact.id,
            owner_user_id=uuid4(),
            revoked_at=revoked_at,
        )
        is None
    )


@pytest.mark.integration
async def test_share_lifecycle_revokes_and_detaches_source_provenance_before_deletes(
    db_session: AsyncSession,
) -> None:
    now = datetime(2026, 4, 30, tzinfo=timezone.utc)
    owner_user_id, roster_id, template_id, draft_id = await _seed_owner_and_draft(
        db_session=db_session,
        now=now,
    )
    repository = PostgreSQLClassroomPlannerShareArtifactRepository(db_session)
    artifact = await repository.create(
        artifact=_artifact(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            template_id=template_id,
            draft_id=draft_id,
            now=now,
        )
    )
    await db_session.commit()

    revoked_at = datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert (
        await repository.revoke_for_draft_lifecycle(
            owner_user_id=owner_user_id,
            draft_id=draft_id,
            draft_kind=PlanDraftKind.GROUPING,
            revoked_at=revoked_at,
        )
        == 1
    )
    await db_session.execute(delete(PlanDraftModel).where(PlanDraftModel.id == draft_id))
    draft_revoked = await repository.get_by_id(share_id=artifact.id)
    assert draft_revoked is not None
    assert draft_revoked.revoked_at == revoked_at
    assert draft_revoked.draft_id is None

    # Reattach a fresh draft to prove roster and template lifecycle paths also
    # detach draft provenance before source records are deleted.
    next_draft_id = uuid4()
    db_session.add(
        PlanDraftModel(
            id=next_draft_id,
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.GROUPING.value,
            template_id=template_id,
            task_entry_classroom_selection_mode=ClassroomSelectionMode.OPTIONAL.value,
            status=PlanDraftStatus.ACTIVE.value,
            revision=4,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.execute(
        update(ClassroomPlannerShareArtifactModel)
        .where(ClassroomPlannerShareArtifactModel.id == artifact.id)
        .values(
            draft_id=next_draft_id,
            roster_id=roster_id,
            template_id=template_id,
            revoked_at=None,
        )
    )
    await db_session.flush()

    assert (
        await repository.revoke_for_template_lifecycle(
            owner_user_id=owner_user_id,
            template_id=template_id,
            revoked_at=revoked_at,
        )
        == 1
    )
    await db_session.execute(delete(RoomTemplateModel).where(RoomTemplateModel.id == template_id))
    template_revoked = await repository.get_by_id(share_id=artifact.id)
    assert template_revoked is not None
    assert template_revoked.draft_id is None
    assert template_revoked.template_id is None

    assert (
        await repository.revoke_for_roster_lifecycle(
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            revoked_at=revoked_at,
        )
        == 1
    )
    await db_session.execute(delete(RosterModel).where(RosterModel.id == roster_id))
    roster_revoked = await repository.get_by_id(share_id=artifact.id)
    assert roster_revoked is not None
    assert roster_revoked.roster_id is None

    assert (
        await repository.revoke_for_owner_lifecycle(
            owner_user_id=owner_user_id,
            revoked_at=revoked_at,
            detach_owner=True,
        )
        == 1
    )
    await db_session.execute(delete(UserModel).where(UserModel.id == owner_user_id))
    owner_revoked = await repository.get_by_id(share_id=artifact.id)
    assert owner_revoked is not None
    assert owner_revoked.owner_user_id is None
    assert owner_revoked.revoked_at == revoked_at
