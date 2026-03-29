"""Focused smart-grouping precedence tests.

This module locks the initial smart-grouping semantics for `ST-27-04` without
waiting for the full export-checkpoint and API slice to land.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
    NormalizedGroupingGroup,
    NormalizedGroupingSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    GroupAssignment,
    RelationshipKind,
    RelationshipRule,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    LiveSeatingContinuityInput,
    solve_smart_grouping,
)

_NOW = datetime(2026, 3, 29, tzinfo=timezone.utc)


def _roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id="ada", display_name="Ada"),
            Student(id="alan", display_name="Alan"),
            Student(id="bea", display_name="Bea"),
            Student(id="cai", display_name="Cai"),
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _groups() -> list[DraftGroup]:
    return [
        DraftGroup(id="group-a", name="Grupp 1", sort_order=0, name_is_custom=False),
        DraftGroup(id="group-b", name="Grupp 2", sort_order=1, name_is_custom=False),
    ]


def _current_group_assignments() -> list[GroupAssignment]:
    return [
        GroupAssignment(student_id="ada", group_id="group-a"),
        GroupAssignment(student_id="alan", group_id="group-a"),
        GroupAssignment(student_id="bea", group_id="group-b"),
        GroupAssignment(student_id="cai", group_id="group-b"),
    ]


def _history_checkpoint(*, groups: list[list[str]]) -> GroupingExportCheckpoint:
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=uuid4(),
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        assignment_hash="checkpoint-hash",
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[NormalizedGroupingGroup(student_ids=group) for group in groups],
            ungrouped_student_ids=[],
        ),
        created_at=_NOW,
    )


def _live_seating() -> LiveSeatingContinuityInput:
    return LiveSeatingContinuityInput(
        seats=[
            Seat(id="seat-1", x=0, y=0),
            Seat(id="seat-2", x=1, y=0),
            Seat(id="seat-3", x=0, y=1),
            Seat(id="seat-4", x=1, y=1),
        ],
        seat_assignments=[
            SeatAssignment(student_id="ada", seat_id="seat-1"),
            SeatAssignment(student_id="alan", seat_id="seat-2"),
            SeatAssignment(student_id="bea", seat_id="seat-3"),
            SeatAssignment(student_id="cai", seat_id="seat-4"),
        ],
    )


def _assignment_map(result) -> dict[str, str]:
    return {assignment.student_id: assignment.group_id for assignment in result.group_assignments}


def test_keep_near_prefers_same_group_in_grouping() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="near-1",
                    kind=RelationshipKind.KEEP_NEAR,
                    student_ids=["ada", "alan"],
                )
            ],
        ),
        current_group_assignments=[],
        history_checkpoints=[],
        live_seating_continuity=None,
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] == assignments_by_student["alan"]


def test_grouping_history_penalizes_label_insensitive_pair_repeats() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(roster_id=roster.id),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[
            _history_checkpoint(groups=[["ada", "alan"], ["bea", "cai"]]),
        ],
        live_seating_continuity=None,
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] != assignments_by_student["alan"]
    assert assignments_by_student["bea"] != assignments_by_student["cai"]


def test_live_seating_continuity_outranks_rerun_diversity() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(roster_id=roster.id),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[],
        live_seating_continuity=_live_seating(),
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] == assignments_by_student["alan"]
    assert assignments_by_student["bea"] == assignments_by_student["cai"]


def test_explicit_rules_outrank_live_seating_continuity() -> None:
    roster = _roster()
    result = solve_smart_grouping(
        roster=roster,
        groups=_groups(),
        smart_rules=RosterSmartRules(
            roster_id=roster.id,
            relationship_rules=[
                RelationshipRule(
                    id="apart-1",
                    kind=RelationshipKind.KEEP_APART,
                    student_ids=["ada", "alan"],
                )
            ],
        ),
        current_group_assignments=_current_group_assignments(),
        history_checkpoints=[],
        live_seating_continuity=_live_seating(),
    )

    assignments_by_student = _assignment_map(result)
    assert assignments_by_student["ada"] != assignments_by_student["alan"]
