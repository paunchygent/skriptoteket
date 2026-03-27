"""Pure smart-seating solver tests for rule scoring and rerun diversity."""

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomSeat,
    NormalizedSeatingSnapshot,
    NormalizedSeatPlacement,
    SeatingExportCheckpoint,
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RelationshipRule,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import solve_smart_seating


def _roster(student_ids: list[str]) -> Roster:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id=student_id, display_name=student_id.title()) for student_id in student_ids
        ],
        created_at=now,
        updated_at=now,
    )


def _template() -> RoomTemplate:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="Sal 101",
        grid_cols=4,
        grid_rows=3,
        seats=[
            Seat(id="front-left", x=0, y=0),
            Seat(id="front-right", x=1, y=0),
            Seat(id="back-left", x=0, y=1),
            Seat(id="back-right", x=1, y=1),
        ],
        fixtures=[
            RoomFixture(
                id="board-1",
                type=RoomFixtureType.WHITEBOARD,
                x=0,
                y=0,
                width=1,
                height=1,
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _rules(
    *,
    near_teacher: list[str] | None = None,
    keep_near: list[list[str]] | None = None,
    keep_apart: list[list[str]] | None = None,
) -> RosterSmartRules:
    return RosterSmartRules(
        roster_id=uuid4(),
        revision=0,
        seating_preferences=[
            StudentSeatingPreference(student_id=student_id, near_teacher=True)
            for student_id in (near_teacher or [])
        ],
        relationship_rules=[
            *[
                RelationshipRule(
                    id=f"near-{index}",
                    kind=RelationshipKind.KEEP_NEAR,
                    student_ids=student_ids,
                )
                for index, student_ids in enumerate(keep_near or [])
            ],
            *[
                RelationshipRule(
                    id=f"apart-{index}",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=student_ids,
                )
                for index, student_ids in enumerate(keep_apart or [])
            ],
        ],
    )


def _checkpoint(*, roster_id, placements: list[tuple[str, str]]) -> SeatingExportCheckpoint:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        template_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="room-hash",
        assignment_hash="assignment-hash",
        room_context=SeatingRoomContextSnapshot(
            grid_cols=4,
            grid_rows=3,
            seats=[
                NormalizedRoomSeat(id="front-left", x=0, y=0),
                NormalizedRoomSeat(id="front-right", x=1, y=0),
                NormalizedRoomSeat(id="back-left", x=0, y=1),
                NormalizedRoomSeat(id="back-right", x=1, y=1),
            ],
            fixtures=[
                {
                    "id": "board-1",
                    "type": "whiteboard",
                    "x": 0,
                    "y": 0,
                    "width": 1,
                    "height": 1,
                    "label": None,
                }
            ],
        ),
        seating_snapshot=NormalizedSeatingSnapshot(
            placed_assignments=[
                NormalizedSeatPlacement(student_id=student_id, seat_id=seat_id)
                for student_id, seat_id in placements
            ],
            unplaced_student_ids=[],
        ),
        created_at=now,
    )


def _assignment_map(result) -> dict[str, str]:
    return {assignment.student_id: assignment.seat_id for assignment in result.seat_assignments}


def test_smart_seating_prefers_near_teacher_students_toward_front() -> None:
    roster = _roster(["ada", "alan"])
    result = solve_smart_seating(
        roster=roster,
        template=_template(),
        smart_rules=_rules(near_teacher=["ada"]),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assignments = _assignment_map(result)
    assert assignments["ada"] in {"front-left", "front-right"}


def test_smart_seating_avoids_direct_orthogonal_adjacency_for_keep_apart() -> None:
    roster = _roster(["ada", "alan", "grace", "linus"])
    result = solve_smart_seating(
        roster=roster,
        template=_template(),
        smart_rules=_rules(keep_apart=[["ada", "alan"]]),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assignments = _assignment_map(result)
    assert {assignments["ada"], assignments["alan"]} in (
        {"front-left", "back-right"},
        {"front-right", "back-left"},
    )


def test_smart_seating_prefers_local_vicinity_for_keep_near() -> None:
    roster = _roster(["ada", "alan", "grace", "linus"])
    result = solve_smart_seating(
        roster=roster,
        template=_template(),
        smart_rules=_rules(keep_near=[["ada", "alan"]]),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assignments = _assignment_map(result)
    assert {assignments["ada"], assignments["alan"]} in (
        {"front-left", "front-right"},
        {"back-left", "back-right"},
        {"front-left", "back-left"},
        {"front-right", "back-right"},
    )


def test_smart_seating_uses_history_to_balance_teacher_distance_over_time() -> None:
    roster = _roster(["ada", "alan"])
    checkpoint = _checkpoint(
        roster_id=roster.id,
        placements=[("alan", "front-left"), ("ada", "back-right")],
    )

    result = solve_smart_seating(
        roster=roster,
        template=_template(),
        smart_rules=_rules(),
        current_seat_assignments=[],
        history_checkpoints=[checkpoint],
    )

    assignments = _assignment_map(result)
    assert assignments["alan"] in {"back-left", "back-right"}


def test_smart_seating_prefers_a_different_strong_candidate_on_rerun() -> None:
    roster = _roster(["ada", "alan"])
    current_assignments = [
        SeatAssignment(student_id="ada", seat_id="front-left"),
        SeatAssignment(student_id="alan", seat_id="front-right"),
    ]

    result = solve_smart_seating(
        roster=roster,
        template=_template(),
        smart_rules=_rules(),
        current_seat_assignments=current_assignments,
        history_checkpoints=[],
    )

    assignments = _assignment_map(result)
    assert assignments != {"ada": "front-left", "alan": "front-right"}
