"""Room-scale smart-seating solver proofs for G20 / SA24D.

This module verifies that the domain solver preserves teacher-zone,
keep-near, keep-apart, history rerun, and solver-owned diagnostic contracts in
the canonical classroom scenario used by Klassrumskartan.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    keep_apart_has_tradeoff as _keep_apart_has_tradeoff,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    keep_apart_pair_score as _keep_apart_pair_score,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    keep_near_has_tradeoff as _keep_near_has_tradeoff,
)
from tests.unit.domain.curated_apps.classroom_planner.smart_seating_solver_scenarios import (
    HISTORY_RERUN_COUNT,
    KEEP_APART_STUDENT_IDS,
    KEEP_NEAR_STUDENT_IDS,
    NEAR_TEACHER_STUDENT_IDS,
    ScenarioRun,
    ScenarioSimulation,
    build_g20_template,
    simulate_g20_sa24d_runs,
)

pytestmark = pytest.mark.simulation

_MIN_VALID_LAYOUT_COUNT = 10
_MIN_DISTINCT_SEAT_COUNT = 2
_MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT = 3
_MIN_NEAR_TEACHER_ROTATION_POOL_SIZE = 5
_MIN_KEEP_APART_MEAN_DISTANCE = 7.0
_MIN_KEEP_APART_BLOCK_COUNT = 2


def _near_teacher_valid(run: ScenarioRun, _: SeatTopology) -> bool:
    return all(
        diagnostic.status == "satisfied"
        for diagnostic in run.rule_diagnostics
        if diagnostic.rule_kind == "near_teacher"
    )


def _keep_near_valid(run: ScenarioRun, topology: SeatTopology) -> bool:
    pair = topology.pair(
        run.assignments_by_student[KEEP_NEAR_STUDENT_IDS[0]],
        run.assignments_by_student[KEEP_NEAR_STUDENT_IDS[1]],
    )
    return pair.keep_near_relation_mode == "adjacent-row"


def _keep_apart_valid(run: ScenarioRun, topology: SeatTopology) -> bool:
    for index, left_id in enumerate(KEEP_APART_STUDENT_IDS):
        for right_id in KEEP_APART_STUDENT_IDS[index + 1 :]:
            pair = topology.pair(
                run.assignments_by_student[left_id],
                run.assignments_by_student[right_id],
            )
            if pair.orthogonally_adjacent or pair.diagonal_neighbor:
                return False
    return True


def _has_no_failed_or_pending_diagnostics(run: ScenarioRun) -> bool:
    return all(
        diagnostic.status not in {"failed", "pending"} for diagnostic in run.rule_diagnostics
    )


def _near_teacher_occupied_seat_ids(simulation: ScenarioSimulation) -> frozenset[str]:
    return frozenset(
        run.assignments_by_student[student_id]
        for run in simulation.runs
        for student_id in NEAR_TEACHER_STUDENT_IDS
    )


def _distinct_seat_counts_by_student(
    simulation: ScenarioSimulation,
    *,
    student_ids: tuple[str, ...] | frozenset[str] | None = None,
) -> dict[str, int]:
    tracked_student_ids = set(student_ids or simulation.runs[0].assignments_by_student)
    return {
        student_id: len({run.assignments_by_student[student_id] for run in simulation.runs})
        for student_id in tracked_student_ids
    }


@pytest.fixture(scope="module")
def g20_sa24d_history_simulation() -> ScenarioSimulation:
    return simulate_g20_sa24d_runs(run_count=HISTORY_RERUN_COUNT, use_history=True)


def test_g20_immediate_diagonal_is_invalid_keep_apart_geometry() -> None:
    template = build_g20_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    pair = topology.pair("seat-2", "seat-12")

    assert pair.diagonal_neighbor is True
    assert _keep_apart_has_tradeoff(pair) is True
    assert _keep_apart_pair_score(pair=pair) < 0.0


def test_g20_pair_keep_near_requires_direct_same_row_contact() -> None:
    template = build_g20_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    same_column_pair = topology.pair("seat-1", "seat-10")
    diagonal_pair = topology.pair("seat-1", "seat-11")

    assert same_column_pair.keep_near_relation_mode == "adjacent-column"
    assert diagonal_pair.diagonal_neighbor is True
    assert _keep_near_has_tradeoff(pair=same_column_pair, cluster_size=2) is True
    assert _keep_near_has_tradeoff(pair=diagonal_pair, cluster_size=2) is True


@pytest.mark.parametrize("use_history", [False, True], ids=["no-history", "with-history"])
def test_g20_sa24d_initial_run_keeps_teacher_rule_contract(use_history: bool) -> None:
    simulation = simulate_g20_sa24d_runs(run_count=1, use_history=use_history)
    run = simulation.runs[0]

    assert _has_no_failed_or_pending_diagnostics(run)
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
    validator: Callable[[ScenarioRun, SeatTopology], bool],
    g20_sa24d_history_simulation: ScenarioSimulation,
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
    g20_sa24d_history_simulation: ScenarioSimulation,
) -> None:
    if rotation_scope == "all_students":
        assert (
            min(_distinct_seat_counts_by_student(g20_sa24d_history_simulation).values())
            >= _MIN_DISTINCT_SEAT_COUNT
        )
        return
    if rotation_scope == "near_teacher":
        _assert_near_teacher_rotation(g20_sa24d_history_simulation)
        return
    if rotation_scope == "keep_near":
        _assert_keep_near_rotation(g20_sa24d_history_simulation)
        return
    distinct_seat_counts = _distinct_seat_counts_by_student(
        g20_sa24d_history_simulation,
        student_ids=KEEP_APART_STUDENT_IDS,
    )
    assert min(distinct_seat_counts.values()) >= _MIN_DISTINCT_SEAT_COUNT


def _assert_near_teacher_rotation(simulation: ScenarioSimulation) -> None:
    distinct_seat_counts = _distinct_seat_counts_by_student(
        simulation,
        student_ids=NEAR_TEACHER_STUDENT_IDS,
    )
    occupied_pool_seat_ids = _near_teacher_occupied_seat_ids(simulation)
    assert min(distinct_seat_counts.values()) >= _MIN_NEAR_TEACHER_DISTINCT_SEAT_COUNT
    assert occupied_pool_seat_ids <= simulation.near_teacher_pool_seat_ids
    assert len(occupied_pool_seat_ids) >= _MIN_NEAR_TEACHER_ROTATION_POOL_SIZE


def _assert_keep_near_rotation(simulation: ScenarioSimulation) -> None:
    distinct_seat_counts = _distinct_seat_counts_by_student(
        simulation,
        student_ids=KEEP_NEAR_STUDENT_IDS,
    )
    keep_near_modes = {
        simulation.topology.pair(
            run.assignments_by_student[KEEP_NEAR_STUDENT_IDS[0]],
            run.assignments_by_student[KEEP_NEAR_STUDENT_IDS[1]],
        ).keep_near_relation_mode
        for run in simulation.runs
    }
    keep_near_modes.discard(None)
    assert min(distinct_seat_counts.values()) >= _MIN_DISTINCT_SEAT_COUNT
    assert keep_near_modes == {"adjacent-row"}


def test_g20_sa24d_history_reruns_stay_valid_and_diverse(
    g20_sa24d_history_simulation: ScenarioSimulation,
) -> None:
    runs = g20_sa24d_history_simulation.runs

    assert all(_has_no_failed_or_pending_diagnostics(run) for run in runs)
    assert min(run.keep_apart_block_count for run in runs) >= _MIN_KEEP_APART_BLOCK_COUNT
    assert min(run.keep_apart_mean_distance for run in runs) >= _MIN_KEEP_APART_MEAN_DISTANCE
    assert len({run.signature for run in runs}) >= _MIN_VALID_LAYOUT_COUNT
