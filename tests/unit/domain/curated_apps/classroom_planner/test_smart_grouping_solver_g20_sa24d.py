"""Real-room smart-grouping scenario tests for G20 / SA24D.

This module reuses the canonical SA24D roster and G20 seat map from the
smart-seating simulations, but it verifies grouping-specific behavior:
explicit grouping rules, grouping-history diversity, and seating continuity as
an input signal.
"""

from __future__ import annotations

import pytest

from tests.unit.domain.curated_apps.classroom_planner.smart_grouping_simulation_support import (
    ScenarioSimulation,
    build_live_seating_input,
    build_roster,
    build_rules,
    build_template,
    keep_apart_valid,
    keep_near_valid,
    same_group_run_count,
    simulate_runs,
    student_id,
)

pytestmark = pytest.mark.simulation

_HISTORY_RERUN_COUNT = 16
_MIN_VALID_LAYOUT_COUNT = 10
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
_KEEP_NEAR_PAIR = (
    student_id("Otilia Olofsson Reijer"),
    student_id("Mary Parsons"),
)
_KEEP_APART_CLUSTER = (
    student_id("Petter Odehn"),
    student_id("Viktor Thornblad"),
    student_id("Leo Svartling"),
    student_id("Vincent Strandberg Gunnarsson"),
    student_id("Lucas Kristiansson"),
    student_id("Liam Vesterberg"),
)
_CONTINUITY_PAIRS = (
    (student_id("Kerstin Aitman"), student_id("Alva Andblad")),
    (student_id("Sofia Andersson"), student_id("Elliot Antonsson")),
)


def _simulate(*, use_history: bool, live_seating: bool) -> ScenarioSimulation:
    roster = build_roster(name="SA24D", student_names=_SA24D_STUDENT_NAMES)
    template = build_template(name="G20", seat_coords=_G20_SEAT_COORDS)
    return simulate_runs(
        roster=roster,
        group_count=8,
        rules=build_rules(
            roster_id=roster.id,
            keep_near_clusters=(_KEEP_NEAR_PAIR,),
            keep_apart_clusters=(_KEEP_APART_CLUSTER,),
            near_teacher_student_ids=(
                student_id("Elliot Antonsson"),
                student_id("Julia Post"),
            ),
        ),
        run_count=_HISTORY_RERUN_COUNT,
        use_history=use_history,
        live_seating_continuity=(
            build_live_seating_input(
                template=template,
                tracked_pairs=_CONTINUITY_PAIRS,
            )
            if live_seating
            else None
        ),
    )


@pytest.fixture(scope="module")
def g20_sa24d_history_simulation() -> ScenarioSimulation:
    return _simulate(use_history=True, live_seating=False)


@pytest.fixture(scope="module")
def g20_sa24d_history_with_live_seating_simulation() -> ScenarioSimulation:
    return _simulate(use_history=True, live_seating=True)


def test_g20_sa24d_history_reruns_keep_grouping_rules_invariant(
    g20_sa24d_history_simulation: ScenarioSimulation,
) -> None:
    invalid_indices = [
        index
        for index, run in enumerate(g20_sa24d_history_simulation.runs, start=1)
        if not keep_near_valid(run, _KEEP_NEAR_PAIR)
        or not keep_apart_valid(run, _KEEP_APART_CLUSTER)
    ]

    assert invalid_indices == []
    assert all(run.has_tradeoffs is False for run in g20_sa24d_history_simulation.runs)


def test_g20_sa24d_history_reruns_diversify_group_partitions(
    g20_sa24d_history_simulation: ScenarioSimulation,
) -> None:
    assert (
        len({run.signature for run in g20_sa24d_history_simulation.runs}) >= _MIN_VALID_LAYOUT_COUNT
    )


def test_g20_sa24d_live_seating_input_keeps_tracked_pairs_together() -> None:
    baseline = _simulate(use_history=False, live_seating=False)
    continuity = _simulate(use_history=True, live_seating=True)

    for tracked_pair in _CONTINUITY_PAIRS:
        assert same_group_run_count(baseline, pair=tracked_pair) == 0
        assert same_group_run_count(continuity, pair=tracked_pair) == _HISTORY_RERUN_COUNT
