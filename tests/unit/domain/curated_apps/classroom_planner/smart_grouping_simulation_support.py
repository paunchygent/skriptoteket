"""Shared support for real-classroom smart-grouping simulations.

This module keeps the simulation harness for `ST-27-04` small and consistent
across the canonical classroom scenarios. It intentionally reuses the same
real roster names and room seat maps as the smart-seating simulations, but it
only measures grouping behavior, grouping-history diversity, and seating as an
input signal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unicodedata import normalize
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
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
    Student,
    StudentSeatingPreference,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    LiveSeatingContinuityInput,
    solve_smart_grouping,
)

_NOW = datetime(2026, 3, 29, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ScenarioRun:
    """Capture one grouping run for repeatable scenario assertions."""

    assignments_by_student: dict[str, str]
    signature: tuple[tuple[str, ...], ...]
    has_tradeoffs: bool


@dataclass(frozen=True)
class ScenarioSimulation:
    """Hold one sampled simulation lane for grouping assertions."""

    runs: list[ScenarioRun]


def student_id(name: str) -> str:
    """Return one stable ASCII student identifier derived from display text."""

    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


def build_roster(*, name: str, student_names: tuple[str, ...]) -> Roster:
    """Build one real-class roster from the canonical scenario names."""

    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name=name,
        students=[
            Student(id=student_id(student_name), display_name=student_name)
            for student_name in student_names
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def build_template(*, name: str, seat_coords: tuple[tuple[int, int], ...]) -> RoomTemplate:
    """Build one room template using the canonical seat map for the scenario."""

    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name=name,
        grid_cols=14,
        grid_rows=10,
        seats=[
            Seat(id=f"seat-{index}", x=x, y=y) for index, (x, y) in enumerate(seat_coords, start=1)
        ],
        fixtures=[],
        created_at=_NOW,
        updated_at=_NOW,
    )


def build_groups(*, group_count: int) -> list[DraftGroup]:
    """Build one stable set of draft-local groups for the simulation."""

    return [
        DraftGroup(
            id=f"group-{index}",
            name=f"Grupp {index}",
            sort_order=index - 1,
            name_is_custom=False,
        )
        for index in range(1, group_count + 1)
    ]


def build_rules(
    *,
    roster_id,
    keep_near_clusters: tuple[tuple[str, ...], ...] = (),
    keep_apart_clusters: tuple[tuple[str, ...], ...] = (),
    near_teacher_student_ids: tuple[str, ...] = (),
) -> RosterSmartRules:
    """Build one rule set for the grouping simulation scenario."""

    relationship_rules: list[RelationshipRule] = []
    for index, cluster in enumerate(keep_near_clusters, start=1):
        relationship_rules.append(
            RelationshipRule(
                id=f"near-{index}",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=list(cluster),
            )
        )
    for index, cluster in enumerate(keep_apart_clusters, start=1):
        relationship_rules.append(
            RelationshipRule(
                id=f"apart-{index}",
                kind=RelationshipKind.KEEP_APART,
                student_ids=list(cluster),
            )
        )
    return RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[
            StudentSeatingPreference(student_id=student_id_value, near_teacher=True)
            for student_id_value in near_teacher_student_ids
        ],
        relationship_rules=relationship_rules,
    )


def build_live_seating_input(
    *,
    template: RoomTemplate,
    tracked_pairs: tuple[tuple[str, str], ...],
) -> LiveSeatingContinuityInput:
    """Map tracked student pairs onto adjacent seats in the canonical room."""

    seat_ids = [seat.id for seat in template.seats]
    seat_assignments: list[SeatAssignment] = []
    next_seat_index = 0
    for left_id, right_id in tracked_pairs:
        seat_assignments.append(
            SeatAssignment(student_id=left_id, seat_id=seat_ids[next_seat_index])
        )
        seat_assignments.append(
            SeatAssignment(student_id=right_id, seat_id=seat_ids[next_seat_index + 1])
        )
        next_seat_index += 3
    return LiveSeatingContinuityInput(
        seats=list(template.seats),
        seat_assignments=seat_assignments,
    )


def simulate_runs(
    *,
    roster: Roster,
    group_count: int,
    rules: RosterSmartRules,
    run_count: int,
    use_history: bool,
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> ScenarioSimulation:
    """Sample repeated grouping reruns with optional history and seating input."""

    current_assignments: list[GroupAssignment] = []
    history_checkpoints: list[GroupingExportCheckpoint] = []
    runs: list[ScenarioRun] = []
    groups = build_groups(group_count=group_count)
    for offset in range(run_count):
        result = solve_smart_grouping(
            roster=roster,
            groups=groups,
            smart_rules=rules,
            current_group_assignments=current_assignments,
            history_checkpoints=history_checkpoints if use_history else [],
            live_seating_continuity=live_seating_continuity,
        )
        assignments_by_student = assignment_map(result.group_assignments)
        runs.append(
            ScenarioRun(
                assignments_by_student=assignments_by_student,
                signature=normalized_signature(assignments_by_student),
                has_tradeoffs=result.has_tradeoffs,
            )
        )
        current_assignments = [
            GroupAssignment(student_id=student_id_value, group_id=group_id)
            for student_id_value, group_id in assignments_by_student.items()
        ]
        if use_history:
            history_checkpoints.append(
                build_grouping_checkpoint(
                    roster_id=roster.id,
                    assignments_by_student=assignments_by_student,
                    offset=offset,
                )
            )
    return ScenarioSimulation(runs=runs)


def assignment_map(group_assignments: list[GroupAssignment]) -> dict[str, str]:
    """Return one student-to-group lookup for the solver output."""

    return {assignment.student_id: assignment.group_id for assignment in group_assignments}


def normalized_signature(assignments_by_student: dict[str, str]) -> tuple[tuple[str, ...], ...]:
    """Return one label-insensitive group partition signature."""

    groups: dict[str, list[str]] = defaultdict(list)
    for student_id_value, group_id in assignments_by_student.items():
        groups[group_id].append(student_id_value)
    return tuple(
        sorted(
            (tuple(sorted(student_ids)) for student_ids in groups.values()),
            key=lambda group: (len(group), group),
        )
    )


def build_grouping_checkpoint(
    *,
    roster_id,
    assignments_by_student: dict[str, str],
    offset: int,
) -> GroupingExportCheckpoint:
    """Convert one simulated grouping result into export-backed history."""

    groups: dict[str, list[str]] = defaultdict(list)
    for student_id_value, group_id in assignments_by_student.items():
        groups[group_id].append(student_id_value)
    return GroupingExportCheckpoint(
        id=uuid4(),
        roster_id=roster_id,
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        assignment_hash=f"grouping-history-{offset}",
        grouping_snapshot=NormalizedGroupingSnapshot(
            groups=[
                NormalizedGroupingGroup(student_ids=sorted(student_ids))
                for student_ids in groups.values()
            ],
            ungrouped_student_ids=[],
        ),
        created_at=_NOW - timedelta(days=offset),
    )


def keep_near_valid(run: ScenarioRun, pair: tuple[str, str]) -> bool:
    """Return whether one explicit keep-near pair stayed together."""

    left_id, right_id = pair
    return run.assignments_by_student[left_id] == run.assignments_by_student[right_id]


def keep_apart_valid(run: ScenarioRun, cluster: tuple[str, ...]) -> bool:
    """Return whether one explicit keep-apart cluster stayed separated."""

    assigned_groups = {run.assignments_by_student[student_id_value] for student_id_value in cluster}
    return len(assigned_groups) == len(cluster)


def same_group_run_count(
    simulation: ScenarioSimulation,
    *,
    pair: tuple[str, str],
) -> int:
    """Count how many runs kept one student pair in the same group."""

    left_id, right_id = pair
    return sum(
        run.assignments_by_student[left_id] == run.assignments_by_student[right_id]
        for run in simulation.runs
    )
