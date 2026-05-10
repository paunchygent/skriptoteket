"""Canonical G20/SA24D smart-seating solver scenarios.

This module owns the reusable room-scale fixture and simulation builders used
by solver tests. Keeping the scenario construction separate lets the tests
focus on domain assertions while preserving one shared classroom model for
history, teacher-zone, relationship, and diagnostic-contract proofs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from unicodedata import normalize
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    NormalizedRoomFixture,
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
from skriptoteket.domain.curated_apps.classroom_planner.seat_support_context import (
    build_seat_support_context,
    desired_near_teacher_seat_ids,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    SmartSeatingResult,
    solve_smart_seating,
)

_NOW = datetime(2026, 3, 27, tzinfo=timezone.utc)
HISTORY_RERUN_COUNT = 240
_HISTORY_CHECKPOINT_COUNT = 6
_SA24D_STUDENT_NAMES = (
    "Kerstin Aitman",
    "Alva Andblad",
    "Sofia Andersson",
    "Elliot Antonsson",
    "Julia Axelsson",
    "Freja Essle",
    "Hilda Grahn",
    "Inger Isfeldt",
    "Nora Johansson",
    "Nellie Jonson",
    "Ella Kjellman",
    "Alexander Klemets",
    "Lucas Kristiansson",
    "Agnes Leandersson",
    "Molly Neijlind",
    "Petter Odehn",
    "Ellen Odenman",
    "Otilia Olofsson Reijer",
    "Vilma Ossner",
    "Mary Parsons",
    "Julia Post",
    "Lily Sandahl",
    "Nora Schneider",
    "Vincent Strandberg Gunnarsson",
    "Leo Svartling",
    "Moa Svensson",
    "Viktor Thornblad",
    "Linnea Walfridson",
    "Liam Vesterberg",
    "Alma Winald",
    "Edith Winlund Strandler",
)
_G20_SEAT_COORDS = (
    (864, 192),
    (960, 192),
    (1056, 192),
    (0, 384),
    (96, 384),
    (192, 384),
    (384, 384),
    (480, 384),
    (576, 384),
    (864, 384),
    (960, 384),
    (1056, 384),
    (0, 576),
    (96, 576),
    (192, 576),
    (384, 576),
    (480, 576),
    (576, 576),
    (864, 576),
    (960, 576),
    (1056, 576),
    (0, 768),
    (96, 768),
    (192, 768),
    (384, 768),
    (480, 768),
    (576, 768),
    (768, 768),
    (864, 768),
    (960, 768),
    (1056, 768),
)
_G20_BENCH_POSITIONS = (
    *((x, y) for y in (288, 480, 672) for x in (0, 96, 192)),
    *((x, y) for y in (288, 480, 672) for x in (384, 480, 576)),
    *((x, y) for y in (96, 288, 480, 672) for x in (864, 960, 1056)),
    (768, 672),
)


def student_id(name: str) -> str:
    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


NEAR_TEACHER_STUDENT_IDS = frozenset(
    {student_id(name) for name in ("Elliot Antonsson", "Julia Post")}
)
KEEP_NEAR_STUDENT_IDS = (student_id("Otilia Olofsson Reijer"), student_id("Mary Parsons"))
KEEP_APART_STUDENT_IDS = (
    student_id("Petter Odehn"),
    student_id("Viktor Thornblad"),
    student_id("Leo Svartling"),
    student_id("Vincent Strandberg Gunnarsson"),
    student_id("Lucas Kristiansson"),
    student_id("Liam Vesterberg"),
)


@dataclass(frozen=True)
class ScenarioRun:
    """Capture one smart-seating run for real-room statistical assertions."""

    assignments_by_student: dict[str, str]
    keep_apart_block_count: int
    keep_apart_mean_distance: float
    rule_diagnostics: tuple[SmartRuleDiagnostic, ...]
    signature: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ScenarioSimulation:
    """Hold the shared topology plus the sampled smart-seating runs."""

    topology: SeatTopology
    near_teacher_pool_seat_ids: frozenset[str]
    runs: list[ScenarioRun]


def build_g20_template() -> RoomTemplate:
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="G20",
        grid_cols=12,
        grid_rows=9,
        seats=[
            Seat(id=f"seat-{index}", x=x, y=y)
            for index, (x, y) in enumerate(_G20_SEAT_COORDS, start=1)
        ],
        fixtures=[
            RoomFixture(
                id=fixture_id, type=fixture_type, x=x, y=y, width=width, height=height, label=label
            )
            for fixture_id, fixture_type, x, y, width, height, label in (
                ("whiteboard-a", RoomFixtureType.WHITEBOARD, 96, 0, 288, 96, "Whiteboard"),
                ("whiteboard-b", RoomFixtureType.WHITEBOARD, 384, 0, 288, 96, "Whiteboard"),
                ("whiteboard-c", RoomFixtureType.WHITEBOARD, 672, 0, 288, 96, "Whiteboard"),
                ("teacher-desk", RoomFixtureType.TEACHER_DESK, 0, 96, 192, 96, "Kateder"),
                ("door-a", RoomFixtureType.DOOR, 0, 192, 96, 96, None),
                *[
                    (f"bench-{index}", RoomFixtureType.BENCH, x, y, 96, 96, None)
                    for index, (x, y) in enumerate(_G20_BENCH_POSITIONS, start=1)
                ],
            )
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def build_g20_roster() -> Roster:
    return _build_roster()


def build_g20_room_context(template: RoomTemplate) -> SeatingRoomContextSnapshot:
    return _build_room_context(template)


def build_g20_history_checkpoints(
    *,
    roster: Roster,
    template: RoomTemplate,
) -> list[SeatingExportCheckpoint]:
    return _build_history_checkpoints(roster=roster, template=template)


def simulate_g20_sa24d_runs(*, run_count: int, use_history: bool) -> ScenarioSimulation:
    roster = _build_roster()
    template = build_g20_template()
    rules = _build_rules(roster_id=roster.id)
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    support_context = build_seat_support_context(
        seats=template.seats,
        fixtures=template.fixtures,
        anchor=infer_teaching_anchor(template=template),
    )
    near_teacher_pool_seat_ids = frozenset(
        desired_near_teacher_seat_ids(topology=topology, support_context=support_context)
    )
    history_checkpoints = _build_history_checkpoints(roster=roster, template=template)
    if not use_history:
        history_checkpoints = []

    runs: list[ScenarioRun] = []
    current_assignments: list[SeatAssignment] = []
    for _ in range(run_count):
        result = solve_smart_seating(
            roster=roster,
            template=template,
            smart_rules=rules,
            current_seat_assignments=current_assignments,
            history_checkpoints=history_checkpoints,
        )
        assignments_by_student = _assignment_map(result)
        runs.append(
            _build_scenario_run(
                assignments_by_student=assignments_by_student,
                rule_diagnostics=result.rule_diagnostics,
                topology=topology,
            )
        )
        current_assignments = [
            SeatAssignment(student_id=student_id, seat_id=seat_id)
            for student_id, seat_id in assignments_by_student.items()
        ]
    return ScenarioSimulation(
        topology=topology,
        near_teacher_pool_seat_ids=near_teacher_pool_seat_ids,
        runs=runs,
    )


def _build_roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id=student_id(student_name), display_name=student_name)
            for student_name in _SA24D_STUDENT_NAMES
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_rules(*, roster_id) -> RosterSmartRules:
    return RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[
            StudentSeatingPreference(student_id=tracked_id, near_teacher=True)
            for tracked_id in sorted(NEAR_TEACHER_STUDENT_IDS)
        ],
        relationship_rules=[
            RelationshipRule(
                id="apart-a",
                kind=RelationshipKind.KEEP_APART,
                student_ids=list(KEEP_APART_STUDENT_IDS),
            ),
            RelationshipRule(
                id="near-b",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=list(KEEP_NEAR_STUDENT_IDS),
            ),
        ],
    )


def _build_room_context(template: RoomTemplate) -> SeatingRoomContextSnapshot:
    return SeatingRoomContextSnapshot(
        grid_cols=template.grid_cols,
        grid_rows=template.grid_rows,
        seats=[NormalizedRoomSeat(id=seat.id, x=seat.x, y=seat.y) for seat in template.seats],
        fixtures=[
            NormalizedRoomFixture(
                id=fixture.id,
                type=fixture.type,
                x=fixture.x,
                y=fixture.y,
                width=fixture.width,
                height=fixture.height,
                label=fixture.label,
            )
            for fixture in template.fixtures
        ],
    )


def _build_history_checkpoints(
    *,
    roster: Roster,
    template: RoomTemplate,
) -> list[SeatingExportCheckpoint]:
    room_context = _build_room_context(template)
    seat_ids = [seat.id for seat in template.seats]
    student_ids = [student.id for student in roster.students]

    checkpoints: list[SeatingExportCheckpoint] = []
    for offset in range(_HISTORY_CHECKPOINT_COUNT):
        rotated_seat_ids = seat_ids[offset:] + seat_ids[:offset]
        checkpoints.append(
            SeatingExportCheckpoint(
                id=uuid4(),
                roster_id=roster.id,
                template_id=template.id,
                source_draft_id=uuid4(),
                source_export_job_id=uuid4(),
                room_context_hash="g20-hash",
                assignment_hash=f"assign-{offset}",
                room_context=room_context,
                seating_snapshot=NormalizedSeatingSnapshot(
                    placed_assignments=[
                        NormalizedSeatPlacement(student_id=tracked_id, seat_id=seat_id)
                        for tracked_id, seat_id in zip(student_ids, rotated_seat_ids, strict=True)
                    ],
                    unplaced_student_ids=[],
                ),
                created_at=_NOW - timedelta(days=offset),
            )
        )
    return checkpoints


def _assignment_map(result: SmartSeatingResult) -> dict[str, str]:
    return {assignment.student_id: assignment.seat_id for assignment in result.seat_assignments}


def _build_scenario_run(
    *,
    assignments_by_student: dict[str, str],
    rule_diagnostics: tuple[SmartRuleDiagnostic, ...],
    topology: SeatTopology,
) -> ScenarioRun:
    pair_distances = [
        topology.pair(
            assignments_by_student[left_id], assignments_by_student[right_id]
        ).grid_manhattan
        for index, left_id in enumerate(KEEP_APART_STUDENT_IDS)
        for right_id in KEEP_APART_STUDENT_IDS[index + 1 :]
    ]
    keep_apart_block_count = len(
        {
            topology.block_id_by_seat[assignments_by_student[student_id]]
            for student_id in KEEP_APART_STUDENT_IDS
        }
    )
    return ScenarioRun(
        assignments_by_student=assignments_by_student,
        keep_apart_block_count=keep_apart_block_count,
        keep_apart_mean_distance=mean(pair_distances),
        rule_diagnostics=rule_diagnostics,
        signature=tuple(sorted(assignments_by_student.items())),
    )
