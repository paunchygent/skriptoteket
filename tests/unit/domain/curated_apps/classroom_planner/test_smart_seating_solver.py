"""Real-room smart-seating scenario tests for G20 / SA24D.

This module replaces toy solver checks with one canonical classroom scenario so
the assertions track repeated reruns and checkpoint history at room scale.
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
    _keep_apart_has_tradeoff,
    _keep_apart_pair_score,
    _keep_near_has_tradeoff,
    solve_smart_seating,
)

pytestmark = pytest.mark.simulation

_NOW = datetime(2026, 3, 27, tzinfo=timezone.utc)
_HISTORY_CHECKPOINT_COUNT = 6
_HISTORY_RERUN_COUNT = 240
_MIN_VALID_LAYOUT_COUNT = 10
_MIN_DISTINCT_SEAT_COUNT = 2
_MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT = 3
_MIN_NEAR_TEACHER_ROTATION_POOL_SIZE = 6
_MIN_KEEP_APART_MEAN_DISTANCE = 7.0
_MIN_KEEP_APART_BLOCK_COUNT = 2
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


def _student_id(name: str) -> str:
    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


_NEAR_TEACHER_STUDENT_IDS = frozenset(
    {_student_id(name) for name in ("Elliot Antonsson", "Julia Post")}
)
_KEEP_NEAR_STUDENT_IDS = (_student_id("Otilia Olofsson Reijer"), _student_id("Mary Parsons"))
_KEEP_APART_STUDENT_IDS = (
    _student_id("Petter Odehn"),
    _student_id("Viktor Thornblad"),
    _student_id("Leo Svartling"),
    _student_id("Vincent Strandberg Gunnarsson"),
    _student_id("Lucas Kristiansson"),
    _student_id("Liam Vesterberg"),
)


@dataclass(frozen=True)
class _ScenarioRun:
    """Capture one smart-seating run for real-room statistical assertions."""

    assignments_by_student: dict[str, str]
    keep_apart_block_count: int
    keep_apart_mean_distance: float
    has_tradeoffs: bool
    signature: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class _ScenarioSimulation:
    """Hold the shared topology plus the sampled smart-seating runs."""

    topology: SeatTopology
    runs: list[_ScenarioRun]


def _build_roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="SA24D",
        students=[
            Student(id=_student_id(student_name), display_name=student_name)
            for student_name in _SA24D_STUDENT_NAMES
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_template() -> RoomTemplate:
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
            ),
            RelationshipRule(
                id="near-b",
                kind=RelationshipKind.KEEP_NEAR,
                student_ids=list(_KEEP_NEAR_STUDENT_IDS),
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
    keep_apart_block_count = len(
        {
            topology.block_id_by_seat[assignments_by_student[student_id]]
            for student_id in _KEEP_APART_STUDENT_IDS
        }
    )
    return _ScenarioRun(
        assignments_by_student=assignments_by_student,
        keep_apart_block_count=keep_apart_block_count,
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


def _near_teacher_valid(run: _ScenarioRun, _: SeatTopology) -> bool:
    return all(
        run.assignments_by_student[student_id]
        in frozenset(_.near_teacher_pool(seat_count=len(_NEAR_TEACHER_STUDENT_IDS) + 1))
        for student_id in _NEAR_TEACHER_STUDENT_IDS
    )


def _keep_near_valid(run: _ScenarioRun, topology: SeatTopology) -> bool:
    pair = topology.pair(
        run.assignments_by_student[_KEEP_NEAR_STUDENT_IDS[0]],
        run.assignments_by_student[_KEEP_NEAR_STUDENT_IDS[1]],
    )
    return pair.orthogonally_adjacent


def _keep_apart_valid(run: _ScenarioRun, topology: SeatTopology) -> bool:
    for index, left_id in enumerate(_KEEP_APART_STUDENT_IDS):
        for right_id in _KEEP_APART_STUDENT_IDS[index + 1 :]:
            pair = topology.pair(
                run.assignments_by_student[left_id],
                run.assignments_by_student[right_id],
            )
            if pair.orthogonally_adjacent or pair.diagonal_neighbor:
                return False
    return True


def test_g20_immediate_diagonal_is_invalid_keep_apart_geometry() -> None:
    template = _build_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    pair = topology.pair("seat-2", "seat-12")

    assert pair.diagonal_neighbor is True
    assert _keep_apart_has_tradeoff(pair) is True
    assert _keep_apart_pair_score(pair=pair) < 0.0


def test_g20_pair_keep_near_requires_direct_row_or_column_contact() -> None:
    template = _build_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    pair = topology.pair("seat-1", "seat-11")

    assert pair.diagonal_neighbor is True
    assert _keep_near_has_tradeoff(pair=pair, cluster_size=2) is True


def _near_teacher_occupied_seat_ids(simulation: _ScenarioSimulation) -> frozenset[str]:
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
def g20_sa24d_history_simulation() -> _ScenarioSimulation:
    return _simulate_runs(run_count=_HISTORY_RERUN_COUNT, use_history=True)


@pytest.mark.parametrize("use_history", [False, True], ids=["no-history", "with-history"])
def test_g20_sa24d_initial_run_keeps_teacher_rule_contract(use_history: bool) -> None:
    simulation = _simulate_runs(run_count=1, use_history=use_history)
    run = simulation.runs[0]

    assert run.has_tradeoffs is False
    assert _near_teacher_valid(run, simulation.topology)
    assert _keep_near_valid(run, simulation.topology)
    assert _keep_apart_valid(run, simulation.topology)


@pytest.mark.parametrize(
    ("rule_name", "validator"),
    [
        ("near_teacher", _near_teacher_valid),
        ("keep_near", _keep_near_valid),
        ("keep_apart", _keep_apart_valid),
    ],
    ids=["near-teacher", "keep-near", "keep-apart"],
)
def test_g20_sa24d_history_reruns_keep_each_rule_invariant(
    rule_name: str,
    validator,
    g20_sa24d_history_simulation: _ScenarioSimulation,
) -> None:
    del rule_name
    invalid_indices = [
        index
        for index, run in enumerate(g20_sa24d_history_simulation.runs, start=1)
        if not validator(run, g20_sa24d_history_simulation.topology)
    ]

    assert invalid_indices == []


@pytest.mark.parametrize(
    "rotation_scope",
    ["all_students", "near_teacher", "keep_near", "keep_apart"],
)
def test_g20_sa24d_history_reruns_rotate_each_rule_lane(
    rotation_scope: str,
    g20_sa24d_history_simulation: _ScenarioSimulation,
) -> None:
    if rotation_scope == "all_students":
        assert (
            min(_distinct_seat_counts_by_student(g20_sa24d_history_simulation).values())
            >= _MIN_DISTINCT_SEAT_COUNT
        )
        return
    if rotation_scope == "near_teacher":
        distinct_seat_counts = _distinct_seat_counts_by_student(
            g20_sa24d_history_simulation,
            student_ids=_NEAR_TEACHER_STUDENT_IDS,
        )
        occupied_pool_seat_ids = _near_teacher_occupied_seat_ids(g20_sa24d_history_simulation)
        teacher_pool_seat_ids = frozenset(
            g20_sa24d_history_simulation.topology.near_teacher_pool(
                seat_count=len(_NEAR_TEACHER_STUDENT_IDS)
            )
        )
        # The teacher-zone lane should stay broad overall even when one specific
        # student's viable front-row subpool narrows under stricter pair geometry.
        assert min(distinct_seat_counts.values()) >= _MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT
        assert occupied_pool_seat_ids <= teacher_pool_seat_ids
        assert len(occupied_pool_seat_ids) >= _MIN_NEAR_TEACHER_ROTATION_POOL_SIZE
        return
    if rotation_scope == "keep_near":
        distinct_seat_counts = _distinct_seat_counts_by_student(
            g20_sa24d_history_simulation,
            student_ids=_KEEP_NEAR_STUDENT_IDS,
        )
        keep_near_modes = {
            g20_sa24d_history_simulation.topology.pair(
                run.assignments_by_student[_KEEP_NEAR_STUDENT_IDS[0]],
                run.assignments_by_student[_KEEP_NEAR_STUDENT_IDS[1]],
            ).keep_near_relation_mode
            for run in g20_sa24d_history_simulation.runs
        }
        keep_near_modes.discard(None)
        assert min(distinct_seat_counts.values()) >= _MIN_DISTINCT_SEAT_COUNT
        assert keep_near_modes <= {"adjacent-row", "adjacent-column"}
        assert len(keep_near_modes) >= 2
        return
    distinct_seat_counts = _distinct_seat_counts_by_student(
        g20_sa24d_history_simulation,
        student_ids=_KEEP_APART_STUDENT_IDS,
    )
    assert min(distinct_seat_counts.values()) >= _MIN_DISTINCT_SEAT_COUNT


def test_g20_sa24d_history_reruns_stay_perfect_and_diverse(
    g20_sa24d_history_simulation: _ScenarioSimulation,
) -> None:
    runs = g20_sa24d_history_simulation.runs

    assert all(run.has_tradeoffs is False for run in runs)
    assert min(run.keep_apart_block_count for run in runs) >= _MIN_KEEP_APART_BLOCK_COUNT
    assert min(run.keep_apart_mean_distance for run in runs) >= _MIN_KEEP_APART_MEAN_DISTANCE
    assert len({run.signature for run in runs}) >= _MIN_VALID_LAYOUT_COUNT
