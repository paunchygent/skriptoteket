"""Fixed-seat smart-seating solver tests.

This module exercises `Fast plats` as a hard seeded assignment while keeping
the existing smart-seat scoring aware of fixed peers in the merged candidate
mapping.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    RelationshipKind,
    RelationshipRule,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    SmartSeatingResult,
    solve_smart_seating,
)
from skriptoteket.domain.errors import DomainError

_NOW = datetime(2026, 5, 5, tzinfo=timezone.utc)


def _roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id="fixed", display_name="Fixed"),
            Student(id="peer", display_name="Peer"),
            Student(id="other", display_name="Other"),
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _template() -> RoomTemplate:
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="Sal 101",
        grid_cols=6,
        grid_rows=2,
        seats=[
            Seat(id="fixed-seat", x=0, y=0),
            Seat(id="near-seat", x=1, y=0),
            Seat(id="far-seat", x=5, y=0),
        ],
        fixtures=[],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _assignment_map(result: SmartSeatingResult) -> dict[str, str]:
    return {assignment.student_id: assignment.seat_id for assignment in result.seat_assignments}


def test_fixed_seat_seeds_hard_assignment_and_keep_near_scores_against_it() -> None:
    roster = _roster()
    template = _template()
    result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="near-1",
                    kind=RelationshipKind.KEEP_NEAR,
                    student_ids=["fixed", "peer"],
                )
            ],
            fixed_seat_rules=[
                FixedSeatRule(
                    id="fixed-1",
                    template_id=template.id,
                    student_id="fixed",
                    seat_id="fixed-seat",
                )
            ],
        ),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assert _assignment_map(result)["fixed"] == "fixed-seat"
    assert _assignment_map(result)["peer"] == "near-seat"


def test_fixed_seat_keep_apart_peer_scores_against_seeded_mapping() -> None:
    roster = _roster()
    template = _template()
    result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="apart-1",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=["fixed", "peer"],
                )
            ],
            fixed_seat_rules=[
                FixedSeatRule(
                    id="fixed-1",
                    template_id=template.id,
                    student_id="fixed",
                    seat_id="fixed-seat",
                )
            ],
        ),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assert _assignment_map(result)["fixed"] == "fixed-seat"
    assert _assignment_map(result)["peer"] == "far-seat"


def test_fixed_seat_leaves_near_teacher_scoring_on_remaining_seats() -> None:
    roster = _roster()
    template = _template()
    result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            seating_preferences=[
                StudentSeatingPreference(student_id="fixed", near_teacher=True),
                StudentSeatingPreference(student_id="peer", near_teacher=True),
            ],
            fixed_seat_rules=[
                FixedSeatRule(
                    id="fixed-1",
                    template_id=template.id,
                    student_id="fixed",
                    seat_id="far-seat",
                )
            ],
        ),
        current_seat_assignments=[],
        history_checkpoints=[],
    )

    assert _assignment_map(result)["fixed"] == "far-seat"
    assert _assignment_map(result)["peer"] == "near-seat"


def test_fixed_seat_rejects_missing_roster_student() -> None:
    roster = _roster()
    template = _template()

    with pytest.raises(DomainError, match="roster students"):
        solve_smart_seating(
            roster=roster,
            template=template,
            smart_rules=RosterSmartRules(
                roster_id=roster.id,
                fixed_seat_rules=[
                    FixedSeatRule(
                        id="fixed-1",
                        template_id=template.id,
                        student_id="missing",
                        seat_id="fixed-seat",
                    )
                ],
            ),
            current_seat_assignments=[],
            history_checkpoints=[],
        )
