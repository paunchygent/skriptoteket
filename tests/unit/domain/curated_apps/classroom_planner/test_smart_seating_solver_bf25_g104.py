"""Real-room smart-seating overlap scenario tests for BF25 / G104.

This module adds a second canonical classroom simulation that covers a
different room topology plus an overlapping-rule student who is both
`Närmare läraren` and part of one `Keep apart` cluster.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from unicodedata import normalize
from uuid import uuid4

import pytest

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
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    SmartSeatingResult,
    solve_smart_seating,
)

pytestmark = pytest.mark.simulation

_NOW = datetime(2026, 3, 28, tzinfo=timezone.utc)
_HISTORY_CHECKPOINT_COUNT = 6
_HISTORY_RERUN_COUNT = 120
_MIN_DISTINCT_SEAT_COUNT = 2
_MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT = 6
_MIN_NEAR_TEACHER_ROTATION_POOL_SIZE = 6
_MIN_VALID_LAYOUT_COUNT = 6
_MIN_KEEP_APART_MEAN_DISTANCE = 11.0
_MIN_KEEP_APART_BLOCK_COUNT = 4
_BF25_STUDENT_NAMES = (
    "Oliver Persson",
    "Anna Nystrom",
    "Felix Larsson",
    "Linus Hakansson",
    "Simon Lundin",
    "Magnus Wikstrom",
    "Julia Berg",
    "Anders Bergstrom",
    "Felix Persson",
    "Elin Danielsson",
    "Selma Lindqvist",
    "Maja Bergman",
    "Lucas Fransson",
    "Linda Pettersson",
    "Selma Arvidsson",
    "Johan Hansson",
    "Ida Holm",
    "Felix Lindberg",
    "Freja Lundin",
    "Per Sjoberg",
    "Vera Berglund",
    "Ella Lindberg",
    "Karin Fransson",
    "Magnus Sandberg",
)
_G104_SEAT_COORDS = (
    (0, 288),
    (288, 288),
    (480, 288),
    (768, 288),
    (960, 288),
    (1248, 288),
    (0, 384),
    (288, 384),
    (480, 384),
    (768, 384),
    (960, 384),
    (1248, 384),
    (0, 672),
    (288, 672),
    (480, 672),
    (768, 672),
    (960, 672),
    (1248, 672),
    (0, 768),
    (288, 768),
    (480, 768),
    (768, 768),
    (960, 768),
    (1248, 768),
)
_G104_FIXTURE_SPECS = (
    ("whiteboard-a", RoomFixtureType.WHITEBOARD, 288, 0, 288, 96, "Whiteboard"),
    ("whiteboard-b", RoomFixtureType.WHITEBOARD, 576, 0, 288, 96, "Whiteboard"),
    ("whiteboard-c", RoomFixtureType.WHITEBOARD, 864, 0, 288, 96, "Whiteboard"),
    ("teacher-desk", RoomFixtureType.TEACHER_DESK, 96, 96, 192, 96, "Kateder"),
    ("door-a", RoomFixtureType.DOOR, 0, 576, 96, 96, None),
    ("table-a", RoomFixtureType.SQUARE_TABLE, 96, 288, 192, 192, None),
    ("table-b", RoomFixtureType.SQUARE_TABLE, 576, 288, 192, 192, None),
    ("table-c", RoomFixtureType.SQUARE_TABLE, 1056, 288, 192, 192, None),
    ("table-d", RoomFixtureType.SQUARE_TABLE, 96, 672, 192, 192, None),
    ("table-e", RoomFixtureType.SQUARE_TABLE, 576, 672, 192, 192, None),
    ("table-f", RoomFixtureType.SQUARE_TABLE, 1056, 672, 192, 192, None),
)


def _student_id(name: str) -> str:
    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


_NEAR_TEACHER_STUDENT_IDS = frozenset({_student_id("Felix Persson")})
_KEEP_APART_STUDENT_IDS = (
    _student_id("Felix Persson"),
    _student_id("Felix Lindberg"),
    _student_id("Simon Lundin"),
    _student_id("Oliver Persson"),
)


@dataclass(frozen=True)
class _ScenarioRun:
    """Capture one smart-seating run for overlap-rule statistical assertions."""

    assignments_by_student: dict[str, str]
    keep_apart_block_count: int
    keep_apart_mean_distance: float
    has_tradeoffs: bool
    signature: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _ScenarioSimulation:
    """Hold the shared topology plus the sampled BF25 / G104 runs."""

    topology: SeatTopology
    runs: list[_ScenarioRun]


def _build_roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="BF25",
        students=[
            Student(id=_student_id(student_name), display_name=student_name)
            for student_name in _BF25_STUDENT_NAMES
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_template() -> RoomTemplate:
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="G104",
        grid_cols=14,
        grid_rows=10,
        seats=[
            Seat(id=f"seat-{index}", x=x, y=y)
            for index, (x, y) in enumerate(_G104_SEAT_COORDS, start=1)
        ],
        fixtures=[
            RoomFixture(
                id=fixture_id,
                type=fixture_type,
                x=x,
                y=y,
                width=width,
                height=height,
                label=label,
            )
            for fixture_id, fixture_type, x, y, width, height, label in _G104_FIXTURE_SPECS
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_rules(*, roster_id) -> RosterSmartRules:
    return RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[
            StudentSeatingPreference(student_id=student_id, near_teacher=True)
            for student_id in sorted(_NEAR_TEACHER_STUDENT_IDS)
        ],
        relationship_rules=[
            RelationshipRule(
                id="apart-a",
                kind=RelationshipKind.KEEP_APART,
                student_ids=list(_KEEP_APART_STUDENT_IDS),
            )
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
                room_context_hash="g104-hash",
                assignment_hash=f"assign-{offset}",
                room_context=room_context,
                seating_snapshot=NormalizedSeatingSnapshot(
                    placed_assignments=[
                        NormalizedSeatPlacement(student_id=student_id, seat_id=seat_id)
                        for student_id, seat_id in zip(student_ids, rotated_seat_ids, strict=True)
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
    has_tradeoffs: bool,
    topology: SeatTopology,
) -> _ScenarioRun:
    pair_distances = [
        topology.pair(
            assignments_by_student[left_id], assignments_by_student[right_id]
        ).grid_manhattan
        for index, left_id in enumerate(_KEEP_APART_STUDENT_IDS)
        for right_id in _KEEP_APART_STUDENT_IDS[index + 1 :]
    ]
    return _ScenarioRun(
        assignments_by_student=assignments_by_student,
        keep_apart_block_count=len(
            {
                topology.block_id_by_seat[assignments_by_student[student_id]]
                for student_id in _KEEP_APART_STUDENT_IDS
            }
        ),
        keep_apart_mean_distance=mean(pair_distances),
        has_tradeoffs=has_tradeoffs,
        signature=tuple(sorted(assignments_by_student.items())),
    )


def _simulate_runs(*, run_count: int, use_history: bool) -> _ScenarioSimulation:
    roster = _build_roster()
    template = _build_template()
    rules = _build_rules(roster_id=roster.id)
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    history_checkpoints = _build_history_checkpoints(roster=roster, template=template)
    if not use_history:
        history_checkpoints = []

    runs: list[_ScenarioRun] = []
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
                has_tradeoffs=result.has_tradeoffs,
                topology=topology,
            )
        )
        current_assignments = [
            SeatAssignment(student_id=student_id, seat_id=seat_id)
            for student_id, seat_id in assignments_by_student.items()
        ]
    return _ScenarioSimulation(topology=topology, runs=runs)


def _near_teacher_valid(run: _ScenarioRun, topology: SeatTopology) -> bool:
    return all(
        run.assignments_by_student[student_id]
        in frozenset(topology.near_teacher_pool(seat_count=len(_NEAR_TEACHER_STUDENT_IDS) + 1))
        for student_id in _NEAR_TEACHER_STUDENT_IDS
    )


def _keep_apart_valid(run: _ScenarioRun, topology: SeatTopology) -> bool:
    for index, left_id in enumerate(_KEEP_APART_STUDENT_IDS):
        for right_id in _KEEP_APART_STUDENT_IDS[index + 1 :]:
            if topology.pair(
                run.assignments_by_student[left_id],
                run.assignments_by_student[right_id],
            ).orthogonally_adjacent:
                return False
    return True


def _near_teacher_occupied_seat_ids(
    simulation: _ScenarioSimulation,
) -> frozenset[str]:
    return frozenset(
        run.assignments_by_student[student_id]
        for run in simulation.runs
        for student_id in _NEAR_TEACHER_STUDENT_IDS
    )


def _distinct_seat_counts_by_student(
    simulation: _ScenarioSimulation,
    *,
    student_ids: tuple[str, ...] | frozenset[str] | None = None,
) -> dict[str, int]:
    tracked_student_ids = set(student_ids or simulation.runs[0].assignments_by_student)
    return {
        student_id: len({run.assignments_by_student[student_id] for run in simulation.runs})
        for student_id in tracked_student_ids
    }


@pytest.fixture(scope="module")
def bf25_g104_history_simulation() -> _ScenarioSimulation:
    return _simulate_runs(run_count=_HISTORY_RERUN_COUNT, use_history=True)


@pytest.mark.parametrize("use_history", [False, True], ids=["no-history", "with-history"])
def test_bf25_g104_initial_run_keeps_overlap_rule_contract(use_history: bool) -> None:
    simulation = _simulate_runs(run_count=1, use_history=use_history)
    run = simulation.runs[0]

    assert run.has_tradeoffs is False
    assert _near_teacher_valid(run, simulation.topology)
    assert _keep_apart_valid(run, simulation.topology)


def test_bf25_g104_history_reruns_keep_overlap_invariants(
    bf25_g104_history_simulation: _ScenarioSimulation,
) -> None:
    invalid_indices = [
        index
        for index, run in enumerate(bf25_g104_history_simulation.runs, start=1)
        if not _near_teacher_valid(run, bf25_g104_history_simulation.topology)
        or not _keep_apart_valid(run, bf25_g104_history_simulation.topology)
    ]
    assert invalid_indices == []


@pytest.mark.parametrize(
    "rotation_scope",
    ["all_students", "near_teacher_overlap", "keep_apart_overlap"],
)
def test_bf25_g104_history_reruns_rotate_overlap_case(
    rotation_scope: str,
    bf25_g104_history_simulation: _ScenarioSimulation,
) -> None:
    if rotation_scope == "all_students":
        assert (
            min(_distinct_seat_counts_by_student(bf25_g104_history_simulation).values())
            >= _MIN_DISTINCT_SEAT_COUNT
        )
        return
    if rotation_scope == "near_teacher_overlap":
        distinct_seat_counts = _distinct_seat_counts_by_student(
            bf25_g104_history_simulation,
            student_ids=_NEAR_TEACHER_STUDENT_IDS,
        )
        occupied_pool_seat_ids = _near_teacher_occupied_seat_ids(bf25_g104_history_simulation)
        teacher_pool_seat_ids = frozenset(
            bf25_g104_history_simulation.topology.near_teacher_pool(
                seat_count=len(_NEAR_TEACHER_STUDENT_IDS)
            )
        )
        assert min(distinct_seat_counts.values()) >= _MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT
        assert occupied_pool_seat_ids <= teacher_pool_seat_ids
        assert len(occupied_pool_seat_ids) >= _MIN_NEAR_TEACHER_ROTATION_POOL_SIZE
        return
    distinct_seat_counts = _distinct_seat_counts_by_student(
        bf25_g104_history_simulation,
        student_ids=_KEEP_APART_STUDENT_IDS,
    )
    assert min(distinct_seat_counts.values()) >= _MIN_DISTINCT_SEAT_COUNT


def test_bf25_g104_history_reruns_stay_perfect_and_diverse(
    bf25_g104_history_simulation: _ScenarioSimulation,
) -> None:
    runs = bf25_g104_history_simulation.runs
    assert all(run.has_tradeoffs is False for run in runs)
    assert min(run.keep_apart_block_count for run in runs) >= _MIN_KEEP_APART_BLOCK_COUNT
    assert min(run.keep_apart_mean_distance for run in runs) >= _MIN_KEEP_APART_MEAN_DISTANCE
    assert len({run.signature for run in runs}) >= _MIN_VALID_LAYOUT_COUNT
