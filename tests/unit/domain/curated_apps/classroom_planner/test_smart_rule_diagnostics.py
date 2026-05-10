"""Solver-owned rule diagnostic tests for Klassrumskartan smart seating.

Purpose:
    Prove the backend diagnostic categories that classroom-map markers render
    for fixed seats, near-teacher preferences, keep-near relationships, and
    keep-apart relationships.

Relationships:
    - Exercises `smart_rule_diagnostics.py` directly at the pure-domain layer.
    - Complements Smart seating application tests that prove DTO exposure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    FixedSeatRule,
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
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
    build_smart_rule_diagnostics,
)

_NOW = datetime(2026, 5, 10, tzinfo=timezone.utc)


def _roster(student_ids: list[str]) -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id=student_id, display_name=f"Student {student_id}")
            for student_id in student_ids
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _template(
    seats: list[Seat],
    fixtures: list[RoomFixture] | None = None,
) -> RoomTemplate:
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="Sal 204",
        grid_cols=12,
        grid_rows=8,
        seats=seats,
        fixtures=fixtures or [],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _fixture(
    fixture_id: str,
    fixture_type: RoomFixtureType,
    *,
    x: int,
    y: int,
    width: int = 96,
    height: int = 96,
) -> RoomFixture:
    return RoomFixture(
        id=fixture_id,
        type=fixture_type,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def _keep_near_rule(rule_id: str, student_ids: list[str]) -> RelationshipRule:
    return RelationshipRule(
        id=rule_id,
        kind=RelationshipKind.KEEP_NEAR,
        student_ids=student_ids,
    )


def _diagnostics(
    *,
    roster: Roster,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    assignments: list[SeatAssignment],
) -> tuple[SmartRuleDiagnostic, ...]:
    return build_smart_rule_diagnostics(
        roster=roster,
        template=template,
        smart_rules=smart_rules,
        seat_assignments=assignments,
    )


def _by_rule_id(
    diagnostics: tuple[SmartRuleDiagnostic, ...],
    rule_id: str,
) -> SmartRuleDiagnostic:
    return next(diagnostic for diagnostic in diagnostics if diagnostic.rule_id == rule_id)


def test_fixed_seat_diagnostics_cover_exact_pending_wrong_and_invalid_states() -> None:
    roster = _roster(["s1", "s2"])
    template = _template([Seat(id="seat-1", x=0, y=0), Seat(id="seat-2", x=96, y=0)])
    base_rule = FixedSeatRule(
        id="fixed-s1",
        template_id=template.id,
        student_id="s1",
        seat_id="seat-1",
    )

    exact = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(roster_id=roster.id, fixed_seat_rules=[base_rule]),
        assignments=[SeatAssignment(student_id="s1", seat_id="seat-1")],
    )
    pending = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(roster_id=roster.id, fixed_seat_rules=[base_rule]),
        assignments=[],
    )
    wrong = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(roster_id=roster.id, fixed_seat_rules=[base_rule]),
        assignments=[SeatAssignment(student_id="s2", seat_id="seat-1")],
    )
    invalid = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            fixed_seat_rules=[
                base_rule.model_copy(update={"id": "fixed-invalid", "seat_id": "missing"})
            ],
        ),
        assignments=[],
    )

    assert _by_rule_id(exact, "fixed-s1").status == "satisfied"
    assert _by_rule_id(pending, "fixed-s1").status == "pending"
    assert _by_rule_id(wrong, "fixed-s1").reason_code == "fixed_seat_wrong_student_in_seat"
    assert _by_rule_id(invalid, "fixed-invalid").reason_code == "fixed_seat_invalid_reference"


def test_near_teacher_rows_treat_first_rank_in_each_column_as_satisfied() -> None:
    roster = _roster(["left", "right", "middle", "back"])
    template = _template(
        [
            Seat(id="front-left", x=0, y=0),
            Seat(id="front-right", x=500, y=0),
            Seat(id="second-left", x=0, y=96),
            Seat(id="third-left", x=0, y=192),
        ],
        [_fixture("board", RoomFixtureType.WHITEBOARD, x=0, y=0, width=500, height=1)],
    )
    rules = RosterSmartRules(
        roster_id=roster.id,
        seating_preferences=[
            StudentSeatingPreference(student_id="right", near_teacher=True),
            StudentSeatingPreference(student_id="middle", near_teacher=True),
            StudentSeatingPreference(student_id="back", near_teacher=True),
        ],
    )
    diagnostics = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="right", seat_id="front-right"),
            SeatAssignment(student_id="middle", seat_id="second-left"),
            SeatAssignment(student_id="back", seat_id="third-left"),
        ],
    )

    assert _by_rule_id(diagnostics, "near_teacher:right").status == "satisfied"
    assert (
        _by_rule_id(diagnostics, "near_teacher:right").reason_code == "near_teacher_row_first_rank"
    )
    assert _by_rule_id(diagnostics, "near_teacher:middle").status == "degraded"
    assert _by_rule_id(diagnostics, "near_teacher:back").status == "failed"


def test_near_teacher_tables_use_two_closest_support_groups_as_satisfied() -> None:
    roster = _roster(["s1", "s2", "s3"])
    seats = [
        Seat(id="table-1-seat", x=0, y=0),
        Seat(id="table-2-seat", x=0, y=160),
        Seat(id="table-3-seat", x=0, y=320),
    ]
    fixtures = [
        _fixture("board", RoomFixtureType.WHITEBOARD, x=0, y=0, height=1),
        _fixture("table-1", RoomFixtureType.ROUND_TABLE, x=0, y=0),
        _fixture("table-2", RoomFixtureType.ROUND_TABLE, x=0, y=160),
        _fixture("table-3", RoomFixtureType.ROUND_TABLE, x=0, y=320),
    ]
    template = _template(seats, fixtures)
    rules = RosterSmartRules(
        roster_id=roster.id,
        seating_preferences=[
            StudentSeatingPreference(student_id="s1", near_teacher=True),
            StudentSeatingPreference(student_id="s2", near_teacher=True),
            StudentSeatingPreference(student_id="s3", near_teacher=True),
        ],
    )
    diagnostics = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="s1", seat_id="table-1-seat"),
            SeatAssignment(student_id="s2", seat_id="table-2-seat"),
            SeatAssignment(student_id="s3", seat_id="table-3-seat"),
        ],
    )

    assert _by_rule_id(diagnostics, "near_teacher:s1").status == "satisfied"
    assert _by_rule_id(diagnostics, "near_teacher:s2").status == "satisfied"
    assert _by_rule_id(diagnostics, "near_teacher:s3").status == "degraded"


def test_keep_near_pair_diagnostics_distinguish_row_and_table_context() -> None:
    roster = _roster(["row-a", "row-b", "row-c", "table-a", "table-b"])
    template = _template(
        [
            Seat(id="row-1", x=0, y=0),
            Seat(id="row-2", x=96, y=0),
            Seat(id="row-across", x=0, y=96),
            Seat(id="table-1", x=288, y=0),
            Seat(id="table-2", x=288, y=96),
        ],
        [_fixture("table", RoomFixtureType.SQUARE_TABLE, x=288, y=0)],
    )
    rules = RosterSmartRules(
        roster_id=roster.id,
        relationship_rules=[
            _keep_near_rule("row-adjacent", ["row-a", "row-b"]),
            _keep_near_rule("row-across", ["row-a", "row-c"]),
            _keep_near_rule("table-pair", ["table-a", "table-b"]),
        ],
    )
    diagnostics = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="row-a", seat_id="row-1"),
            SeatAssignment(student_id="row-b", seat_id="row-2"),
            SeatAssignment(student_id="row-c", seat_id="row-across"),
            SeatAssignment(student_id="table-a", seat_id="table-1"),
            SeatAssignment(student_id="table-b", seat_id="table-2"),
        ],
    )

    assert _by_rule_id(diagnostics, "row-adjacent").status == "satisfied"
    assert _by_rule_id(diagnostics, "row-adjacent").seating_context == "row_layout"
    assert _by_rule_id(diagnostics, "row-across").status == "degraded"
    assert _by_rule_id(diagnostics, "row-across").relation_mode == "adjacent-column"
    assert _by_rule_id(diagnostics, "table-pair").status == "satisfied"
    assert _by_rule_id(diagnostics, "table-pair").seating_context == "shared_table"


def test_keep_near_group_diagnostics_handle_table_split_and_large_stop_rule() -> None:
    roster = _roster(["s1", "s2", "s3", "s4", "s5", "s6", "s7"])
    template = _template(
        [
            Seat(id="table-a-1", x=0, y=0),
            Seat(id="table-a-2", x=96, y=0),
            Seat(id="table-a-3", x=0, y=96),
            Seat(id="table-b-1", x=300, y=0),
            Seat(id="large-1", x=0, y=240),
            Seat(id="large-2", x=96, y=240),
            Seat(id="large-3", x=192, y=240),
            Seat(id="large-4", x=288, y=240),
            Seat(id="large-5", x=384, y=240),
            Seat(id="large-6", x=480, y=240),
            Seat(id="large-7", x=576, y=240),
        ],
        [
            _fixture("table-a", RoomFixtureType.SQUARE_TABLE, x=0, y=0),
            _fixture("table-b", RoomFixtureType.SQUARE_TABLE, x=300, y=0),
        ],
    )
    rules = RosterSmartRules(
        roster_id=roster.id,
        relationship_rules=[
            _keep_near_rule("same-table", ["s1", "s2", "s3"]),
            _keep_near_rule("split-table", ["s1", "s2", "s4"]),
            _keep_near_rule("too-large", ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]),
        ],
    )
    diagnostics = _diagnostics(
        roster=roster,
        template=template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="s1", seat_id="table-a-1"),
            SeatAssignment(student_id="s2", seat_id="table-a-2"),
            SeatAssignment(student_id="s3", seat_id="table-a-3"),
            SeatAssignment(student_id="s4", seat_id="table-b-1"),
            SeatAssignment(student_id="s5", seat_id="large-5"),
            SeatAssignment(student_id="s6", seat_id="large-6"),
            SeatAssignment(student_id="s7", seat_id="large-7"),
        ],
    )

    assert _by_rule_id(diagnostics, "same-table").status == "satisfied"
    assert _by_rule_id(diagnostics, "split-table").status == "failed"
    too_large = _by_rule_id(diagnostics, "too-large")
    assert too_large.status == "degraded"
    assert too_large.message_key == "keep_near_group_too_large"


def test_keep_apart_diagnostics_distinguish_contact_tradeoff_and_separation() -> None:
    roster = _roster(["s1", "s2"])
    compact_template = _template(
        [
            Seat(id="seat-1", x=0, y=0),
            Seat(id="seat-2", x=96, y=0),
            Seat(id="seat-3", x=192, y=0),
            Seat(id="seat-4", x=0, y=96),
            Seat(id="seat-5", x=96, y=96),
            Seat(id="seat-6", x=192, y=96),
            Seat(id="seat-7", x=0, y=192),
            Seat(id="seat-8", x=96, y=192),
            Seat(id="seat-9", x=192, y=192),
        ]
    )
    separated_template = _template(
        [
            Seat(id="left", x=0, y=0),
            Seat(id="buffer", x=100, y=0),
            Seat(id="right", x=400, y=0),
        ]
    )
    rule = RelationshipRule(
        id="apart",
        kind=RelationshipKind.KEEP_APART,
        student_ids=["s1", "s2"],
    )
    rules = RosterSmartRules(roster_id=roster.id, relationship_rules=[rule])

    immediate = _diagnostics(
        roster=roster,
        template=compact_template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="s1", seat_id="seat-1"),
            SeatAssignment(student_id="s2", seat_id="seat-2"),
        ],
    )
    same_zone = _diagnostics(
        roster=roster,
        template=compact_template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="s1", seat_id="seat-1"),
            SeatAssignment(student_id="s2", seat_id="seat-9"),
        ],
    )
    separated = _diagnostics(
        roster=roster,
        template=separated_template,
        smart_rules=rules,
        assignments=[
            SeatAssignment(student_id="s1", seat_id="left"),
            SeatAssignment(student_id="s2", seat_id="right"),
        ],
    )

    assert _by_rule_id(immediate, "apart").status == "failed"
    assert _by_rule_id(same_zone, "apart").status == "degraded"
    assert _by_rule_id(separated, "apart").status == "satisfied"
