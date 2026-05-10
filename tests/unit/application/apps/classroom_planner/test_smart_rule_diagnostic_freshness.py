"""Diagnostic freshness tests for Klassrumskartan marker rehydration.

Purpose:
    Prove solver-owned marker diagnostics are keyed to the full persisted input
    shape instead of transient frontend Smart-run state.

Relationships:
    - Exercises `smart_rule_diagnostic_freshness.py` at the application layer.
    - Complements workspace-load and Smart-run tests that serialize the key.
"""

from datetime import datetime, timezone
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner import (
    smart_rule_diagnostic_freshness as freshness,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
    PlanDraft,
    PlanDraftKind,
    PlanDraftStatus,
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

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
ROSTER_ID = UUID("00000000-0000-0000-0000-000000000002")
TEMPLATE_ID = UUID("00000000-0000-0000-0000-000000000003")
DRAFT_ID = UUID("00000000-0000-0000-0000-000000000004")


def _draft(*, roster_id, template_id, revision=4) -> PlanDraft:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return PlanDraft(
        id=DRAFT_ID,
        owner_user_id=OWNER_ID,
        roster_id=roster_id,
        draft_kind=PlanDraftKind.SEATING,
        template_id=template_id,
        status=PlanDraftStatus.ACTIVE,
        revision=revision,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )


def _roster(*, roster_id=None, student_ids=("ada", "alan")) -> Roster:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return Roster(
        id=roster_id or ROSTER_ID,
        owner_user_id=OWNER_ID,
        name="SA24D",
        students=[
            Student(id=student_id, display_name=student_id.title()) for student_id in student_ids
        ],
        created_at=now,
        updated_at=now,
    )


def _template(*, template_id=None, seat_b_x=1) -> RoomTemplate:
    now = datetime(2026, 5, 10, tzinfo=timezone.utc)
    return RoomTemplate(
        id=template_id or TEMPLATE_ID,
        owner_user_id=OWNER_ID,
        name="Sal 101",
        grid_cols=4,
        grid_rows=3,
        seats=[Seat(id="seat-a", x=0, y=0), Seat(id="seat-b", x=seat_b_x, y=0)],
        fixtures=[
            RoomFixture(
                id="board-1",
                type=RoomFixtureType.WHITEBOARD,
                x=0,
                y=0,
                width=2,
                height=1,
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _rules(
    *,
    roster_id,
    template_id,
    relation_ids=("ada", "alan"),
    revision=2,
) -> RosterSmartRules:
    return RosterSmartRules(
        roster_id=roster_id,
        revision=revision,
        seating_preferences=[StudentSeatingPreference(student_id="ada", near_teacher=True)],
        relationship_rules=[
            RelationshipRule(
                id="near-pair",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=list(relation_ids),
            )
        ],
        fixed_seat_rules=[
            FixedSeatRule(
                id="fixed-ada",
                template_id=template_id,
                student_id="ada",
                seat_id="seat-a",
            )
        ],
    )


def _key(
    *,
    draft_revision=4,
    smart_rule_revision=2,
    student_ids=("ada", "alan"),
    relation_ids=("ada", "alan"),
    seat_b_x=1,
    assignments=(("ada", "seat-a"), ("alan", "seat-b")),
) -> str:
    roster = _roster(student_ids=student_ids)
    template = _template(seat_b_x=seat_b_x)
    return freshness.build_diagnostic_freshness_key(
        draft=_draft(roster_id=roster.id, template_id=template.id, revision=draft_revision),
        roster=roster,
        template=template,
        smart_rules=_rules(
            roster_id=roster.id,
            template_id=template.id,
            relation_ids=relation_ids,
            revision=smart_rule_revision,
        ),
        seat_assignments=[
            SeatAssignment(student_id=student_id, seat_id=seat_id)
            for student_id, seat_id in assignments
        ],
    )


def test_diagnostic_freshness_key_is_stable_for_equivalent_assignment_order() -> None:
    assert _key(assignments=(("ada", "seat-a"), ("alan", "seat-b"))) == _key(
        assignments=(("alan", "seat-b"), ("ada", "seat-a"))
    )


def test_diagnostic_freshness_key_changes_for_solver_input_changes() -> None:
    baseline = _key()

    changed_keys = {
        _key(draft_revision=5),
        _key(smart_rule_revision=3),
        _key(student_ids=("ada", "alan", "grace")),
        _key(relation_ids=("ada", "grace")),
        _key(seat_b_x=2),
        _key(assignments=(("ada", "seat-b"), ("alan", "seat-a"))),
    }

    assert baseline not in changed_keys
    assert len(changed_keys) == 6
