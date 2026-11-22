"""Integration coverage for classroom planner repository read models.

This module verifies that the PostgreSQL classroom-planner repository returns
the class-workspace summary contract with task-separated active drafts,
task-separated history, template labels, and correct roster scoping.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    DraftWorkspace,
    GroupAssignment,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    SeatAssignment,
)
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.classroom_planner_plan_draft import (
    PlanDraftModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.classroom_planner import (
    PostgreSQLPlanDraftRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    """Return a stable timestamp baseline for ordering assertions."""

    return datetime.now(timezone.utc)


@pytest_asyncio.fixture(loop_scope="module")
async def planner_owner_id(db_session: AsyncSession, now: datetime) -> UUID:
    """Create a teacher/user row required by planner repository fixtures."""

    user_id = uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"classroom-planner-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


@pytest.mark.integration
async def test_get_class_workspace_draft_summary_separates_tasks_and_history(
    db_session: AsyncSession,
    planner_owner_id: UUID,
    now: datetime,
) -> None:
    """Return active and historical draft summaries separated by task kind."""

    target_roster_id = uuid4()
    other_roster_id = uuid4()
    active_seating_template_id = uuid4()
    superseded_seating_template_id = uuid4()

    db_session.add_all(
        [
            RosterModel(
                id=target_roster_id,
                owner_user_id=planner_owner_id,
                name="8A",
                students=[
                    {"id": "s-1", "display_name": "Ada"},
                    {"id": "s-2", "display_name": "Bo"},
                ],
                created_at=now,
                updated_at=now,
            ),
            RosterModel(
                id=other_roster_id,
                owner_user_id=planner_owner_id,
                name="9B",
                students=[{"id": "s-3", "display_name": "Cid"}],
                created_at=now,
                updated_at=now,
            ),
            RoomTemplateModel(
                id=active_seating_template_id,
                owner_user_id=planner_owner_id,
                name="Sal A",
                seats=[],
                fixtures=[],
                created_at=now,
                updated_at=now,
            ),
            RoomTemplateModel(
                id=superseded_seating_template_id,
                owner_user_id=planner_owner_id,
                name="Sal B",
                seats=[],
                fixtures=[],
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await db_session.flush()

    active_grouping_id = uuid4()
    abandoned_grouping_newer_id = uuid4()
    superseded_grouping_older_id = uuid4()
    active_seating_id = uuid4()
    abandoned_seating_id = uuid4()
    superseded_seating_id = uuid4()
    other_roster_active_grouping_id = uuid4()

    db_session.add_all(
        [
            PlanDraftModel(
                id=active_grouping_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.GROUPING.value,
                template_id=None,
                status=PlanDraftStatus.ACTIVE.value,
                revision=7,
                last_opened_at=now + timedelta(hours=6),
                created_at=now,
                updated_at=now + timedelta(hours=6),
            ),
            PlanDraftModel(
                id=abandoned_grouping_newer_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.GROUPING.value,
                template_id=None,
                status=PlanDraftStatus.ABANDONED.value,
                revision=6,
                last_opened_at=now + timedelta(hours=5),
                created_at=now,
                updated_at=now + timedelta(hours=5),
            ),
            PlanDraftModel(
                id=superseded_grouping_older_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.GROUPING.value,
                template_id=None,
                status=PlanDraftStatus.SUPERSEDED.value,
                revision=4,
                last_opened_at=now + timedelta(hours=3),
                created_at=now,
                updated_at=now + timedelta(hours=3),
            ),
            PlanDraftModel(
                id=active_seating_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.SEATING.value,
                template_id=active_seating_template_id,
                status=PlanDraftStatus.ACTIVE.value,
                revision=9,
                last_opened_at=now + timedelta(hours=7),
                created_at=now,
                updated_at=now + timedelta(hours=7),
            ),
            PlanDraftModel(
                id=abandoned_seating_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.SEATING.value,
                template_id=active_seating_template_id,
                status=PlanDraftStatus.ABANDONED.value,
                revision=8,
                last_opened_at=now + timedelta(hours=4),
                created_at=now,
                updated_at=now + timedelta(hours=4),
            ),
            PlanDraftModel(
                id=superseded_seating_id,
                owner_user_id=planner_owner_id,
                roster_id=target_roster_id,
                draft_kind=PlanDraftKind.SEATING.value,
                template_id=superseded_seating_template_id,
                status=PlanDraftStatus.SUPERSEDED.value,
                revision=5,
                last_opened_at=now + timedelta(hours=2),
                created_at=now,
                updated_at=now + timedelta(hours=2),
            ),
            PlanDraftModel(
                id=other_roster_active_grouping_id,
                owner_user_id=planner_owner_id,
                roster_id=other_roster_id,
                draft_kind=PlanDraftKind.GROUPING.value,
                template_id=None,
                status=PlanDraftStatus.ACTIVE.value,
                revision=99,
                last_opened_at=now + timedelta(hours=8),
                created_at=now,
                updated_at=now + timedelta(hours=8),
            ),
        ]
    )
    await db_session.flush()

    repository = PostgreSQLPlanDraftRepository(db_session)

    summary = await repository.get_class_workspace_draft_summary(
        owner_user_id=planner_owner_id,
        roster_id=target_roster_id,
        history_limit_per_kind=2,
    )

    assert summary.active_grouping_draft is not None
    assert summary.active_grouping_draft.id == active_grouping_id
    assert summary.active_grouping_draft.draft_kind == PlanDraftKind.GROUPING
    assert summary.active_grouping_draft.template_name is None

    assert summary.active_seating_draft is not None
    assert summary.active_seating_draft.id == active_seating_id
    assert summary.active_seating_draft.draft_kind == PlanDraftKind.SEATING
    assert summary.active_seating_draft.template_name == "Sal A"

    assert [item.id for item in summary.grouping_history] == [
        abandoned_grouping_newer_id,
        superseded_grouping_older_id,
    ]
    assert [item.status for item in summary.grouping_history] == [
        PlanDraftStatus.ABANDONED,
        PlanDraftStatus.SUPERSEDED,
    ]

    assert [item.id for item in summary.seating_history] == [
        abandoned_seating_id,
        superseded_seating_id,
    ]
    assert [item.template_name for item in summary.seating_history] == ["Sal A", "Sal B"]
    assert other_roster_active_grouping_id not in {
        summary.active_grouping_draft.id,
        *(item.id for item in summary.grouping_history),
        *(item.id for item in summary.seating_history),
    }


@pytest.mark.integration
async def test_undo_and_redo_restore_saved_workspace_snapshots(
    db_session: AsyncSession,
    planner_owner_id: UUID,
    now: datetime,
) -> None:
    """Undo and redo re-apply the stored snapshots to flags, groups and assignments."""

    roster_id = uuid4()
    db_session.add(
        RosterModel(
            id=roster_id,
            owner_user_id=planner_owner_id,
            name="8A",
            students=[{"id": "s-1", "display_name": "Ada"}],
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=planner_owner_id,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.GROUPING,
        smart_enabled=False,
        use_history=False,
        grouping_seating_distance_enabled=False,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )
    first = DraftWorkspace(
        draft=draft,
        groups=[DraftGroup(id="g-1", name="Grupp 1", sort_order=0)],
        group_assignments=[GroupAssignment(student_id="s-1", group_id="g-1")],
        seat_assignments=[SeatAssignment(student_id="s-1", seat_id="seat-1")],
    )
    second = DraftWorkspace(
        draft=draft.model_copy(
            update={
                "smart_enabled": True,
                "use_history": True,
                "grouping_seating_distance_enabled": True,
            }
        ),
        groups=[
            DraftGroup(id="g-2", name="Eget namn", sort_order=1, name_is_custom=True),
            DraftGroup(id="g-1", name="Grupp 1", sort_order=0),
        ],
        group_assignments=[GroupAssignment(student_id="s-1", group_id="g-2")],
    )

    repository = PostgreSQLPlanDraftRepository(db_session)
    await repository.save_workspace(workspace=first)
    await repository.save_workspace(workspace=second)

    undone = await repository.undo(draft_id=draft.id)

    assert undone is not None
    assert undone.draft.smart_enabled is False
    assert undone.draft.use_history is False
    assert undone.draft.grouping_seating_distance_enabled is False
    assert undone.draft.template_id is None
    assert [(group.id, group.name_is_custom) for group in undone.groups] == [("g-1", False)]
    assert [(a.student_id, a.group_id) for a in undone.group_assignments] == [("s-1", "g-1")]
    assert [(a.student_id, a.seat_id) for a in undone.seat_assignments] == [("s-1", "seat-1")]
    assert undone.history_status.can_redo is True

    redone = await repository.redo(draft_id=draft.id)

    assert redone is not None
    assert redone.draft.smart_enabled is True
    assert redone.draft.use_history is True
    assert redone.draft.grouping_seating_distance_enabled is True
    assert {(group.id, group.name, group.name_is_custom) for group in redone.groups} == {
        ("g-1", "Grupp 1", False),
        ("g-2", "Eget namn", True),
    }
    assert [(a.student_id, a.group_id) for a in redone.group_assignments] == [("s-1", "g-2")]
    assert redone.seat_assignments == []
