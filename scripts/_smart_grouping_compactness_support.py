"""Support helpers for smart-grouping compactness simulations.

Purpose:
    Reuse the canonical classroom scenarios from the smart seating and smart
    grouping tests, then expose a compact support surface for report scripts.

Relationships:
    - consumed by `scripts.smart_grouping_compactness_simulation_report`
    - delegates analysis to `_smart_grouping_compactness_trials.py`
    - delegates PNG generation to `_smart_grouping_compactness_rendering.py`
"""

from __future__ import annotations

from dataclasses import replace

from scripts._smart_grouping_compactness_models import (
    CandidateReport,
    CandidateSpec,
    ScenarioDefinition,
)
from scripts._smart_grouping_compactness_rendering import render_seating_projection
from scripts._smart_grouping_compactness_trials import (
    candidate_report_payload,
    run_candidate,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    ClassroomCompactnessConfig,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import solve_smart_seating
from tests.unit.domain.curated_apps.classroom_planner import (
    smart_grouping_simulation_support as grouping_support,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_grouping_solver_bf25_g104 as bf25_grouping,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_grouping_solver_g20_sa24d as g20_grouping,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_seating_solver as g20_seating,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    test_smart_seating_solver_bf25_g104 as bf25_seating,
)

_G20_REDUCED_KEEP_APART_CLUSTER = (
    grouping_support.student_id("Petter Odehn"),
    grouping_support.student_id("Viktor Thornblad"),
    grouping_support.student_id("Leo Svartling"),
    grouping_support.student_id("Vincent Strandberg Gunnarsson"),
)
_TRIAL_COUNT = 10
_RANDOMIZED_ORDER_ATTEMPTS = 8

__all__ = [
    "CandidateReport",
    "CandidateSpec",
    "ScenarioDefinition",
    "candidate_report_payload",
    "default_candidate_specs",
    "load_canonical_scenarios",
    "render_seating_projection",
    "run_candidate",
    "with_artifact_path",
]


def load_canonical_scenarios() -> list[ScenarioDefinition]:
    """Build the canonical whole-class seating projections for the first sweep."""

    return [_build_g20_sa24d_scenario(), _build_bf25_g104_scenario()]


def default_candidate_specs() -> tuple[CandidateSpec, ...]:
    """Return the focused method-combination sweep used for the report."""

    return (
        CandidateSpec(
            key="baseline",
            label="Baslinje",
            compactness_config=None,
            trial_count=_TRIAL_COUNT,
            randomized_order_attempts=_RANDOMIZED_ORDER_ATTEMPTS,
        ),
        _candidate_spec(
            key="quadratic",
            label="Kvadratisk",
            include_quadratic=True,
        ),
        _candidate_spec(
            key="quadratic-plus-medoid",
            label="Kvadratisk + mittpunkt",
            include_quadratic=True,
            include_medoid=True,
        ),
        _candidate_spec(
            key="quadratic-plus-components",
            label="Kvadratisk + delytor",
            include_quadratic=True,
            include_components=True,
        ),
        _candidate_spec(
            key="quadratic-plus-bench-chain",
            label="Kvadratisk + bänkkedja",
            include_quadratic=True,
            include_bench_chain=True,
        ),
        _candidate_spec(
            key="hybrid-all",
            label="Kvadratisk + mittpunkt + delytor + block + bänkkedja",
            include_quadratic=True,
            include_medoid=True,
            include_components=True,
            include_block_fit=True,
            include_bench_chain=True,
        ),
    )


def with_artifact_path(
    *,
    report: CandidateReport,
    artifact_path: str,
) -> CandidateReport:
    """Return one report copy with the written artifact path attached."""

    return replace(report, artifact_path=artifact_path)


def _candidate_spec(
    *,
    key: str,
    label: str,
    include_quadratic: bool = False,
    include_medoid: bool = False,
    include_components: bool = False,
    include_block_fit: bool = False,
    include_bench_chain: bool = False,
) -> CandidateSpec:
    return CandidateSpec(
        key=key,
        label=label,
        compactness_config=_compactness_config(
            include_quadratic=include_quadratic,
            include_medoid=include_medoid,
            include_components=include_components,
            include_block_fit=include_block_fit,
            include_bench_chain=include_bench_chain,
        ),
        trial_count=_TRIAL_COUNT,
        randomized_order_attempts=_RANDOMIZED_ORDER_ATTEMPTS,
    )


def _compactness_config(
    *,
    include_quadratic: bool,
    include_medoid: bool,
    include_components: bool,
    include_block_fit: bool,
    include_bench_chain: bool,
) -> ClassroomCompactnessConfig:
    return ClassroomCompactnessConfig(
        elastic_radius=2,
        proximity_reward=2.0 if include_quadratic else 0.0,
        distance_penalty=3.0 if include_quadratic else 0.0,
        disconnected_component_penalty=4.0 if include_components else 0.0,
        singleton_component_penalty=6.0 if include_components else 0.0,
        nearest_component_penalty=1.5 if include_components else 0.0,
        split_block_penalty=4.0 if include_block_fit else 0.0,
        secondary_block_penalty=8.0 if include_block_fit else 0.0,
        secondary_zone_penalty=6.0 if include_bench_chain else 0.0,
        zone_row_gap_penalty=5.0 if include_bench_chain else 0.0,
        center_distance_penalty=2.0 if include_medoid else 0.0,
    )


def _build_g20_sa24d_scenario() -> ScenarioDefinition:
    roster = g20_seating._build_roster()
    template = g20_seating._build_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    reduced_seating_rules = grouping_support.build_rules(
        roster_id=roster.id,
        keep_near_clusters=(g20_grouping._KEEP_NEAR_PAIR,),
        keep_apart_clusters=(_G20_REDUCED_KEEP_APART_CLUSTER,),
        near_teacher_student_ids=tuple(sorted(g20_seating._NEAR_TEACHER_STUDENT_IDS)),
    )
    seating_result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=reduced_seating_rules,
        current_seat_assignments=[],
        history_checkpoints=g20_seating._build_history_checkpoints(
            roster=roster,
            template=template,
        ),
    )
    return ScenarioDefinition(
        key="g20-sa24d",
        label="SA24D i G20",
        roster=roster,
        template=template,
        topology=topology,
        groups=grouping_support.build_groups(group_count=8),
        grouping_rules=grouping_support.build_rules(
            roster_id=roster.id,
            keep_near_clusters=(g20_grouping._KEEP_NEAR_PAIR,),
            keep_apart_clusters=(_G20_REDUCED_KEEP_APART_CLUSTER,),
        ),
        keep_near_pair=g20_grouping._KEEP_NEAR_PAIR,
        keep_apart_cluster=_G20_REDUCED_KEEP_APART_CLUSTER,
        seating_assignments_by_student={
            assignment.student_id: assignment.seat_id
            for assignment in seating_result.seat_assignments
        },
    )


def _build_bf25_g104_scenario() -> ScenarioDefinition:
    roster = bf25_seating._build_roster()
    template = bf25_seating._build_template()
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    seating_result = solve_smart_seating(
        roster=roster,
        template=template,
        smart_rules=bf25_seating._build_rules(roster_id=roster.id),
        current_seat_assignments=[],
        history_checkpoints=bf25_seating._build_history_checkpoints(
            roster=roster,
            template=template,
        ),
    )
    return ScenarioDefinition(
        key="bf25-g104",
        label="BF25 i G104",
        roster=roster,
        template=template,
        topology=topology,
        groups=grouping_support.build_groups(group_count=6),
        grouping_rules=grouping_support.build_rules(
            roster_id=roster.id,
            keep_apart_clusters=(bf25_grouping._KEEP_APART_CLUSTER,),
        ),
        keep_near_pair=None,
        keep_apart_cluster=bf25_grouping._KEEP_APART_CLUSTER,
        seating_assignments_by_student={
            assignment.student_id: assignment.seat_id
            for assignment in seating_result.seat_assignments
        },
    )
