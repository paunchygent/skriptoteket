"""Real-room smart-grouping overlap scenario tests for BF25 / G104.

This module mirrors the canonical BF25 / G104 overlap case from smart
seating, but it verifies the grouping rule precedence: explicit `Keep apart`
must still win even when the live seating input puts the same students next to
each other.
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
    same_group_run_count,
    simulate_runs,
    student_id,
)

pytestmark = pytest.mark.simulation

_HISTORY_RERUN_COUNT = 16
_MIN_VALID_LAYOUT_COUNT = 10
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
_KEEP_APART_CLUSTER = (
    student_id("Felix Persson"),
    student_id("Felix Lindberg"),
    student_id("Simon Lundin"),
    student_id("Oliver Persson"),
)
_OVERLAP_CONTINUITY_PAIR = (
    student_id("Felix Persson"),
    student_id("Felix Lindberg"),
)


def _simulate(*, use_history: bool, live_seating: bool) -> ScenarioSimulation:
    roster = build_roster(name="BF25", student_names=_BF25_STUDENT_NAMES)
    template = build_template(name="G104", seat_coords=_G104_SEAT_COORDS)
    return simulate_runs(
        roster=roster,
        group_count=6,
        rules=build_rules(
            roster_id=roster.id,
            keep_apart_clusters=(_KEEP_APART_CLUSTER,),
            near_teacher_student_ids=(student_id("Felix Persson"),),
        ),
        run_count=_HISTORY_RERUN_COUNT,
        use_history=use_history,
        live_seating_continuity=(
            build_live_seating_input(
                template=template,
                tracked_pairs=(_OVERLAP_CONTINUITY_PAIR,),
            )
            if live_seating
            else None
        ),
    )


@pytest.fixture(scope="module")
def bf25_g104_history_simulation() -> ScenarioSimulation:
    return _simulate(use_history=True, live_seating=False)


@pytest.fixture(scope="module")
def bf25_g104_history_with_live_seating_simulation() -> ScenarioSimulation:
    return _simulate(use_history=True, live_seating=True)


def test_bf25_g104_history_reruns_keep_apart_invariant(
    bf25_g104_history_simulation: ScenarioSimulation,
) -> None:
    invalid_indices = [
        index
        for index, run in enumerate(bf25_g104_history_simulation.runs, start=1)
        if not keep_apart_valid(run, _KEEP_APART_CLUSTER)
    ]

    assert invalid_indices == []
    assert all(run.has_tradeoffs is False for run in bf25_g104_history_simulation.runs)


def test_bf25_g104_history_reruns_diversify_group_partitions(
    bf25_g104_history_simulation: ScenarioSimulation,
) -> None:
    assert (
        len({run.signature for run in bf25_g104_history_simulation.runs}) >= _MIN_VALID_LAYOUT_COUNT
    )


def test_bf25_g104_live_seating_never_overrides_keep_apart(
    bf25_g104_history_with_live_seating_simulation: ScenarioSimulation,
) -> None:
    assert (
        same_group_run_count(
            bf25_g104_history_with_live_seating_simulation,
            pair=_OVERLAP_CONTINUITY_PAIR,
        )
        == 0
    )
