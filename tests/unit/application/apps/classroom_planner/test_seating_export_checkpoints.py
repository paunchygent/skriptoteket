"""Unit tests for classroom-planner seating export checkpoints.

This module locks the normalization and hashing rules for export-backed
seating history so later smart-history consumers can trust the checkpoint
registry without depending on draft ordering or export presentation details.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    build_assignment_hash,
    build_normalized_seating_snapshot,
    build_room_context_hash,
    build_room_context_snapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftHistoryStatus,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    Seat,
    SeatAssignment,
    Student,
)


def _workspace(
    *,
    seat_assignments: list[SeatAssignment],
    seats: list[Seat] | None = None,
    fixtures: list[RoomFixture] | None = None,
) -> ClassroomPlannerWorkspace:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    owner_user_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    return ClassroomPlannerWorkspace(
        draft=PlanDraft(
            id=uuid4(),
            owner_user_id=owner_user_id,
            roster_id=roster_id,
            draft_kind=PlanDraftKind.SEATING,
            template_id=template_id,
            status=PlanDraftStatus.ACTIVE,
            revision=4,
            last_opened_at=now,
            created_at=now,
            updated_at=now,
        ),
        roster=Roster(
            id=roster_id,
            owner_user_id=owner_user_id,
            name="Klass 7A",
            students=[
                Student(id="student-1", display_name="Ada Lovelace"),
                Student(id="student-2", display_name="Linus Torvalds"),
                Student(id="student-3", display_name="Grace Hopper"),
            ],
            created_at=now,
            updated_at=now,
        ),
        template=RoomTemplate(
            id=template_id,
            owner_user_id=owner_user_id,
            name="Sal A",
            seats=seats
            or [
                Seat(id="seat-b", x=96, y=0),
                Seat(id="seat-a", x=0, y=0, zone="front"),
            ],
            fixtures=fixtures
            or [
                RoomFixture(
                    id="board",
                    type=RoomFixtureType.WHITEBOARD,
                    x=0,
                    y=0,
                    width=3,
                    height=1,
                    label="Whiteboard",
                )
            ],
            created_at=now,
            updated_at=now,
        ),
        seat_assignments=seat_assignments,
        history_status=DraftHistoryStatus(can_undo=False, can_redo=False),
    )


@pytest.mark.unit
def test_normalized_seating_snapshot_sorts_assignments_and_tracks_unplaced_students() -> None:
    workspace = _workspace(
        seat_assignments=[
            SeatAssignment(student_id="student-2", seat_id="seat-b"),
            SeatAssignment(student_id="student-1", seat_id="seat-a"),
        ]
    )

    snapshot = build_normalized_seating_snapshot(workspace=workspace)

    assert [(item.seat_id, item.student_id) for item in snapshot.placed_assignments] == [
        ("seat-a", "student-1"),
        ("seat-b", "student-2"),
    ]
    assert snapshot.unplaced_student_ids == ["student-3"]


@pytest.mark.unit
def test_assignment_hash_is_stable_across_input_order_but_changes_when_unplaced_set_changes() -> (
    None
):
    baseline = _workspace(
        seat_assignments=[
            SeatAssignment(student_id="student-2", seat_id="seat-b"),
            SeatAssignment(student_id="student-1", seat_id="seat-a"),
        ]
    )
    reordered = _workspace(
        seat_assignments=[
            SeatAssignment(student_id="student-1", seat_id="seat-a"),
            SeatAssignment(student_id="student-2", seat_id="seat-b"),
        ]
    ).model_copy(
        update={
            "draft": baseline.draft,
            "roster": baseline.roster,
            "template": baseline.template,
        }
    )
    changed = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")]
    ).model_copy(
        update={
            "draft": baseline.draft,
            "roster": baseline.roster,
            "template": baseline.template,
        }
    )

    baseline_hash = build_assignment_hash(
        seating_snapshot=build_normalized_seating_snapshot(workspace=baseline)
    )
    reordered_hash = build_assignment_hash(
        seating_snapshot=build_normalized_seating_snapshot(workspace=reordered)
    )
    changed_hash = build_assignment_hash(
        seating_snapshot=build_normalized_seating_snapshot(workspace=changed)
    )

    assert reordered_hash == baseline_hash
    assert changed_hash != baseline_hash


@pytest.mark.unit
def test_room_context_hash_changes_when_room_geometry_changes() -> None:
    baseline = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")]
    )
    changed_room = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")],
        seats=[
            Seat(id="seat-b", x=192, y=0),
            Seat(id="seat-a", x=0, y=0, zone="front"),
        ],
    ).model_copy(update={"draft": baseline.draft, "roster": baseline.roster})

    baseline_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=baseline)
    )
    changed_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=changed_room)
    )

    assert changed_hash != baseline_hash


@pytest.mark.unit
def test_room_context_hash_ignores_template_identity_and_non_geometry_metadata() -> None:
    baseline = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")]
    )
    copied_template = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="copy-seat-a")],
        seats=[
            Seat(id="copy-seat-b", x=96, y=0, zone="back"),
            Seat(id="copy-seat-a", x=0, y=0),
        ],
        fixtures=[
            RoomFixture(
                id="copy-board",
                type=RoomFixtureType.WHITEBOARD,
                x=0,
                y=0,
                width=3,
                height=1,
                label="Different label",
            )
        ],
    )

    baseline_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=baseline)
    )
    copied_template_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=copied_template)
    )

    assert baseline.template is not None
    assert copied_template.template is not None
    assert baseline.template.id != copied_template.template.id
    assert copied_template_hash == baseline_hash


@pytest.mark.unit
def test_room_context_hash_changes_when_teaching_fixture_type_changes() -> None:
    baseline = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")]
    )
    changed_fixture_type = _workspace(
        seat_assignments=[SeatAssignment(student_id="student-1", seat_id="seat-a")],
        fixtures=[
            RoomFixture(
                id="board-copy",
                type=RoomFixtureType.TEACHER_DESK,
                x=0,
                y=0,
                width=3,
                height=1,
                label="Teacher desk",
            )
        ],
    ).model_copy(update={"draft": baseline.draft, "roster": baseline.roster})

    baseline_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=baseline)
    )
    changed_hash = build_room_context_hash(
        room_context=build_room_context_snapshot(workspace=changed_fixture_type)
    )

    assert changed_hash != baseline_hash
