"""G104 smart-seating proof for normal mixed rule expectations.

Purpose:
    Prove that a realistic rule set with one fixed seat, two near-teacher
    students, one keep-apart pair, and one keep-near pair produces teacher-
    visible rule-pattern variation over ten Smart runs.

Relationships:
    - Exercises the pure smart-seating domain solver with a production-like
      G104 classroom topology.
    - Complements the larger G20/SA24D and BF25/G104 simulation suites by
      treating in-pair swaps as the same teacher-visible pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import blake2b
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
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    solve_smart_seating,
)

pytestmark = pytest.mark.simulation

_NOW = datetime(2026, 5, 12, tzinfo=timezone.utc)
_RUN_COUNT = 10
_STUDENT_NAMES = (
    "Patrik Hansson",
    "Johanna Larsson",
    "Magnus Wikström",
    "Katarina Pettersson",
    "Carina Svensson",
    "Birgitta Håkansson",
    "Felix Lindberg",
    "Anders Bergman",
    "Margareta Karlsson",
    "Camilla Lundin",
    "Caroline Lindberg",
    "Jonas Bergman",
    "Peter Lindqvist",
    "Magnus Sandberg",
    "Ulf Danielsson",
    "Mats Bergström",
    "Lennart Bergqvist",
    "Katarina Svensson",
    "Andreas Fransson",
    "Ingrid Lindqvist",
    "Helena Bergström",
    "Carina Lundin",
    "Ulrika Nilsson",
    "Carina Holmberg",
    "Bengt Fransson",
    "Marcus Lundgren",
    "Oliver Persson",
)
_SEAT_COORDS = tuple(
    (x, y) for y in (288, 480, 672) for x in (0, 96, 192, 480, 576, 672, 960, 1056, 1152)
)
_BENCH_ORIGINS = (
    (0, 288),
    (480, 288),
    (960, 288),
    (0, 480),
    (480, 480),
    (960, 480),
    (0, 672),
    (480, 672),
    (960, 672),
)


@dataclass(frozen=True)
class _ScenarioRun:
    assignments_by_student: dict[str, str]
    rule_block_pattern: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]
    keep_near_seat_set: frozenset[str]
    keep_apart_seat_set: frozenset[str]


@dataclass(frozen=True)
class _ScenarioSimulation:
    topology: SeatTopology
    runs: list[_ScenarioRun]


def _student_id(name: str) -> str:
    normalized = normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace(" ", "-")


NEAR_TEACHER_STUDENT_IDS = frozenset(
    {_student_id("Birgitta Håkansson"), _student_id("Johanna Larsson")}
)
KEEP_NEAR_STUDENT_IDS = (_student_id("Jonas Bergman"), _student_id("Peter Lindqvist"))
KEEP_APART_STUDENT_IDS = (_student_id("Oliver Persson"), _student_id("Patrik Hansson"))


def _build_roster() -> Roster:
    return Roster(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="G104 normal rules",
        students=[
            Student(id=_student_id(student_name), display_name=student_name)
            for student_name in _STUDENT_NAMES
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
            Seat(id=f"seat-{index}", x=x, y=y) for index, (x, y) in enumerate(_SEAT_COORDS, start=1)
        ],
        fixtures=[
            RoomFixture(
                id="whiteboard",
                type=RoomFixtureType.WHITEBOARD,
                x=480,
                y=0,
                width=288,
                height=96,
                label="Whiteboard",
            ),
            RoomFixture(
                id="teacher-desk",
                type=RoomFixtureType.TEACHER_DESK,
                x=96,
                y=96,
                width=192,
                height=96,
                label="Kateder",
            ),
            *[
                RoomFixture(
                    id=f"bench-{index}",
                    type=RoomFixtureType.BENCH,
                    x=x,
                    y=y - 96,
                    width=288,
                    height=48,
                    label=None,
                )
                for index, (x, y) in enumerate(_BENCH_ORIGINS, start=1)
            ],
        ],
        created_at=_NOW,
        updated_at=_NOW,
    )


def _build_rules(*, roster_id, template_id) -> RosterSmartRules:
    return RosterSmartRules(
        roster_id=roster_id,
        revision=0,
        seating_preferences=[
            StudentSeatingPreference(student_id=student_id, near_teacher=True)
            for student_id in sorted(NEAR_TEACHER_STUDENT_IDS)
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
        fixed_seat_rules=[
            FixedSeatRule(
                id="fixed-carina-svensson",
                template_id=template_id,
                student_id=_student_id("Carina Svensson"),
                seat_id="seat-5",
            )
        ],
    )


def _simulate_runs(*, run_count: int, mode: str) -> _ScenarioSimulation:
    roster = _build_roster()
    template = _build_template()
    rules = _build_rules(roster_id=roster.id, template_id=template.id)
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    current_assignments: list[SeatAssignment] = []
    history_checkpoints: list[SeatingExportCheckpoint] = []
    runs: list[_ScenarioRun] = []
    for run_index in range(run_count):
        result = solve_smart_seating(
            roster=roster,
            template=template,
            smart_rules=rules,
            current_seat_assignments=[] if mode == "new_draft_history" else current_assignments,
            history_checkpoints=history_checkpoints if mode == "new_draft_history" else [],
        )
        assignments_by_student = {
            assignment.student_id: assignment.seat_id for assignment in result.seat_assignments
        }
        runs.append(
            _build_run(
                assignments_by_student=assignments_by_student,
                topology=topology,
            )
        )
        current_assignments = [
            SeatAssignment(student_id=student_id, seat_id=seat_id)
            for student_id, seat_id in assignments_by_student.items()
        ]
        if mode == "new_draft_history":
            history_checkpoints.insert(
                0,
                _build_checkpoint(
                    roster=roster,
                    template=template,
                    assignments_by_student=assignments_by_student,
                    run_index=run_index,
                ),
            )
    return _ScenarioSimulation(topology=topology, runs=runs)


def _build_run(
    *,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> _ScenarioRun:
    return _ScenarioRun(
        assignments_by_student=assignments_by_student,
        rule_block_pattern=(
            _block_signature(
                assignments_by_student=assignments_by_student,
                topology=topology,
                student_ids=NEAR_TEACHER_STUDENT_IDS,
            ),
            _block_signature(
                assignments_by_student=assignments_by_student,
                topology=topology,
                student_ids=frozenset(KEEP_NEAR_STUDENT_IDS),
            ),
            _block_signature(
                assignments_by_student=assignments_by_student,
                topology=topology,
                student_ids=frozenset(KEEP_APART_STUDENT_IDS),
            ),
        ),
        keep_near_seat_set=frozenset(
            assignments_by_student[student_id] for student_id in KEEP_NEAR_STUDENT_IDS
        ),
        keep_apart_seat_set=frozenset(
            assignments_by_student[student_id] for student_id in KEEP_APART_STUDENT_IDS
        ),
    )


def _block_signature(
    *,
    assignments_by_student: dict[str, str],
    topology: SeatTopology,
    student_ids: frozenset[str],
) -> tuple[int, ...]:
    return tuple(
        sorted(
            topology.block_id_by_seat[assignments_by_student[student_id]]
            for student_id in student_ids
        )
    )


def _build_checkpoint(
    *,
    roster: Roster,
    template: RoomTemplate,
    assignments_by_student: dict[str, str],
    run_index: int,
) -> SeatingExportCheckpoint:
    signature = tuple(sorted(assignments_by_student.items()))
    assignment_hash = blake2b(repr(signature).encode("utf-8"), digest_size=8).hexdigest()
    return SeatingExportCheckpoint(
        id=uuid4(),
        roster_id=roster.id,
        template_id=template.id,
        source_draft_id=uuid4(),
        source_export_job_id=uuid4(),
        room_context_hash="g104-normal-rules",
        assignment_hash=assignment_hash,
        room_context=SeatingRoomContextSnapshot(
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
        ),
        seating_snapshot=NormalizedSeatingSnapshot(
            placed_assignments=[
                NormalizedSeatPlacement(student_id=student_id, seat_id=seat_id)
                for student_id, seat_id in signature
            ],
            unplaced_student_ids=[],
        ),
        created_at=_NOW + timedelta(minutes=run_index),
    )


@pytest.mark.parametrize(
    "mode",
    ["new_draft_history", "same_draft_no_history"],
)
def test_g104_normal_rules_produce_ten_teacher_visible_block_patterns(mode: str) -> None:
    simulation = _simulate_runs(run_count=_RUN_COUNT, mode=mode)

    assert len({run.rule_block_pattern for run in simulation.runs}) == _RUN_COUNT
    assert len({run.keep_near_seat_set for run in simulation.runs}) >= 6
    assert len({run.keep_apart_seat_set for run in simulation.runs}) >= 6
