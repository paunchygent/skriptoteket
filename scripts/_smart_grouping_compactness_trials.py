"""Trial analysis helpers for smart-grouping compactness simulations.

Purpose:
    Run candidate trials, aggregate best-of metrics, and compute overlay-facing
    topology measures without mixing that logic into scenario setup or drawing.

Relationships:
    - consumed by `_smart_grouping_compactness_support.py`
    - uses scenario/report dataclasses from `_smart_grouping_compactness_models.py`
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from statistics import mean
from typing import Any

from scripts._smart_grouping_compactness_models import (
    CandidateReport,
    CandidateSpec,
    ScenarioDefinition,
    TrialReport,
)
from scripts._smart_grouping_compactness_topology import (
    connected_student_components,
    nearest_component_gap,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import SeatAssignment
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import SeatTopology
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping import (
    ClassroomCompactnessConfig,
    GreedySearchConfig,
    LiveSeatingContinuityInput,
    solve_smart_grouping,
)
from tests.unit.domain.curated_apps.classroom_planner import (
    smart_grouping_simulation_support as grouping_support,
)


def run_candidate(
    *,
    scenario: ScenarioDefinition,
    candidate: CandidateSpec,
) -> CandidateReport:
    """Run one grouping candidate against one fixed whole-class seating map."""

    trials = tuple(
        _run_trial(scenario=scenario, candidate=candidate, trial_index=trial_index)
        for trial_index in range(candidate.trial_count)
    )
    best_trial = max(trials, key=_trial_selection_key)
    return CandidateReport(
        key=candidate.key,
        label=candidate.label,
        trial_count=candidate.trial_count,
        randomized_order_attempts=candidate.randomized_order_attempts,
        best_trial_index=best_trial.trial_index,
        best_random_seed=best_trial.random_seed,
        used_classroom_compactness=candidate.compactness_config is not None,
        compactness_config=(
            asdict(candidate.compactness_config)
            if candidate.compactness_config is not None
            else None
        ),
        rule_valid_rate=sum(1.0 for trial in trials if _trial_rule_valid(trial)) / len(trials),
        keep_near_valid_rate=_rule_rate(
            trials=trials, attr_name="keep_near_valid", enabled=scenario.keep_near_pair is not None
        ),
        keep_apart_valid_rate=_rule_rate(
            trials=trials,
            attr_name="keep_apart_valid",
            enabled=scenario.keep_apart_cluster is not None,
        ),
        zero_fragmentation_rate=sum(1.0 for trial in trials if trial.fragmented_group_count == 0)
        / len(trials),
        zero_singleton_rate=sum(1.0 for trial in trials if trial.singleton_component_count == 0)
        / len(trials),
        zero_split_block_rate=sum(1.0 for trial in trials if trial.split_block_group_count == 0)
        / len(trials),
        zero_zone_spill_rate=sum(1.0 for trial in trials if trial.secondary_zone_student_count == 0)
        / len(trials),
        zero_zone_gap_rate=sum(1.0 for trial in trials if trial.primary_zone_row_gap_count == 0)
        / len(trials),
        assignments_by_student=best_trial.assignments_by_student,
        keep_near_valid=best_trial.keep_near_valid,
        keep_apart_valid=best_trial.keep_apart_valid,
        mean_within_group_distance=best_trial.mean_within_group_distance,
        max_within_group_distance=best_trial.max_within_group_distance,
        fragmented_group_count=best_trial.fragmented_group_count,
        total_group_component_count=best_trial.total_group_component_count,
        singleton_component_count=best_trial.singleton_component_count,
        secondary_component_gap_sum=best_trial.secondary_component_gap_sum,
        split_block_group_count=best_trial.split_block_group_count,
        secondary_block_student_count=best_trial.secondary_block_student_count,
        secondary_zone_student_count=best_trial.secondary_zone_student_count,
        primary_zone_row_gap_count=best_trial.primary_zone_row_gap_count,
        component_student_ids_by_group=best_trial.component_student_ids_by_group,
        artifact_path="",
    )


def candidate_report_payload(candidate_report: CandidateReport) -> dict[str, Any]:
    """Convert one report into a JSON-friendly payload."""

    return asdict(candidate_report)


def run_trial(
    *,
    scenario: ScenarioDefinition,
    candidate: CandidateSpec,
    trial_index: int,
) -> TrialReport:
    """Run one randomized greedy trial for the current candidate."""

    live_seating = _live_seating_input(
        scenario=scenario, use_compactness=candidate.compactness_config is not None
    )
    random_seed = _trial_seed(
        scenario_key=scenario.key,
        candidate_key=candidate.key,
        trial_index=trial_index,
    )
    result = solve_smart_grouping(
        roster=scenario.roster,
        groups=scenario.groups,
        smart_rules=scenario.grouping_rules,
        current_group_assignments=[],
        history_checkpoints=[],
        live_seating_continuity=live_seating,
        classroom_compactness_config=(
            candidate.compactness_config
            if candidate.compactness_config is not None
            else ClassroomCompactnessConfig()
        ),
        greedy_search_config=GreedySearchConfig(
            randomized_order_attempts=candidate.randomized_order_attempts,
            random_seed=random_seed,
        ),
    )
    assignments_by_student = grouping_support.assignment_map(result.group_assignments)
    component_groups = component_student_ids_by_group(
        assignments_by_student=assignments_by_student,
        seating_assignments_by_student=scenario.seating_assignments_by_student,
        topology=scenario.topology,
    )
    mean_distance, max_distance = within_group_distance_metrics(
        assignments_by_student=assignments_by_student,
        seating_assignments_by_student=scenario.seating_assignments_by_student,
        topology=scenario.topology,
    )
    split_block_group_count, secondary_block_student_count = block_fit_metrics(
        assignments_by_student=assignments_by_student,
        seating_assignments_by_student=scenario.seating_assignments_by_student,
        topology=scenario.topology,
    )
    secondary_zone_student_count, primary_zone_row_gap_count = bench_chain_metrics(
        assignments_by_student=assignments_by_student,
        seating_assignments_by_student=scenario.seating_assignments_by_student,
        topology=scenario.topology,
    )
    scenario_run = grouping_support.ScenarioRun(
        assignments_by_student=assignments_by_student,
        signature=grouping_support.normalized_signature(assignments_by_student),
        has_tradeoffs=result.has_tradeoffs,
    )
    return TrialReport(
        trial_index=trial_index,
        random_seed=random_seed,
        assignments_by_student=assignments_by_student,
        keep_near_valid=grouping_support.keep_near_valid(scenario_run, scenario.keep_near_pair)
        if scenario.keep_near_pair is not None
        else None,
        keep_apart_valid=grouping_support.keep_apart_valid(
            scenario_run, scenario.keep_apart_cluster
        )
        if scenario.keep_apart_cluster is not None
        else None,
        mean_within_group_distance=mean_distance,
        max_within_group_distance=max_distance,
        fragmented_group_count=sum(
            1 for components in component_groups.values() if len(components) > 1
        ),
        total_group_component_count=sum(
            len(components) for components in component_groups.values()
        ),
        singleton_component_count=sum(
            sum(1 for component in components if len(component) == 1)
            for components in component_groups.values()
        ),
        secondary_component_gap_sum=secondary_component_gap_sum(
            assignments_by_student=assignments_by_student,
            seating_assignments_by_student=scenario.seating_assignments_by_student,
            topology=scenario.topology,
        ),
        split_block_group_count=split_block_group_count,
        secondary_block_student_count=secondary_block_student_count,
        secondary_zone_student_count=secondary_zone_student_count,
        primary_zone_row_gap_count=primary_zone_row_gap_count,
        component_student_ids_by_group=component_groups,
    )


def _run_trial(
    *,
    scenario: ScenarioDefinition,
    candidate: CandidateSpec,
    trial_index: int,
) -> TrialReport:
    return run_trial(scenario=scenario, candidate=candidate, trial_index=trial_index)


def _trial_selection_key(trial: TrialReport) -> tuple[float, ...]:
    return (
        1.0 if _trial_rule_valid(trial) else 0.0,
        1.0 if trial.keep_apart_valid is not False else 0.0,
        1.0 if trial.keep_near_valid is not False else 0.0,
        -float(trial.fragmented_group_count),
        -float(trial.singleton_component_count),
        -float(trial.split_block_group_count),
        -float(trial.secondary_block_student_count),
        -float(trial.secondary_zone_student_count),
        -float(trial.primary_zone_row_gap_count),
        -float(trial.secondary_component_gap_sum),
        -trial.mean_within_group_distance,
        -float(trial.max_within_group_distance),
        -float(trial.trial_index),
    )


def component_student_ids_by_group(
    *,
    assignments_by_student: dict[str, str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[str, list[list[str]]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    return {
        group_id: connected_student_components(
            student_ids=sorted(student_ids),
            seating_assignments_by_student=seating_assignments_by_student,
            topology=topology,
        )
        for group_id, student_ids in groups.items()
    }


def within_group_distance_metrics(
    *,
    assignments_by_student: dict[str, str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> tuple[float, int]:
    distances: list[int] = []
    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    for student_ids in groups.values():
        ordered = sorted(student_ids)
        for index, left_id in enumerate(ordered):
            for right_id in ordered[index + 1 :]:
                distances.append(
                    topology.pair(
                        seating_assignments_by_student[left_id],
                        seating_assignments_by_student[right_id],
                    ).grid_manhattan
                )
    return (0.0, 0) if not distances else (mean(distances), max(distances))


def secondary_component_gap_sum(
    *,
    assignments_by_student: dict[str, str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> int:
    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    total_gap = 0
    for student_ids in groups.values():
        components = connected_student_components(
            student_ids=sorted(student_ids),
            seating_assignments_by_student=seating_assignments_by_student,
            topology=topology,
        )
        if not components:
            continue
        ordered_components = sorted(components, key=lambda component: (-len(component), component))
        primary_component = ordered_components[0]
        for component in ordered_components[1:]:
            total_gap += nearest_component_gap(
                source_component=component,
                target_component=primary_component,
                seating_assignments_by_student=seating_assignments_by_student,
                topology=topology,
            )
    return total_gap


def block_fit_metrics(
    *,
    assignments_by_student: dict[str, str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> tuple[int, int]:
    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    split_block_group_count = 0
    secondary_block_student_count = 0
    for student_ids in groups.values():
        block_counts: dict[int, int] = defaultdict(int)
        for student_id in student_ids:
            block_counts[topology.block_id_by_seat[seating_assignments_by_student[student_id]]] += 1
        if len(block_counts) > 1:
            split_block_group_count += 1
        primary_block_size = max(block_counts.values(), default=0)
        secondary_block_student_count += max(len(student_ids) - primary_block_size, 0)
    return split_block_group_count, secondary_block_student_count


def bench_chain_metrics(
    *,
    assignments_by_student: dict[str, str],
    seating_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> tuple[int, int]:
    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    secondary_zone_student_count = 0
    primary_zone_row_gap_count = 0
    for student_ids in groups.values():
        zone_counts: dict[int, int] = defaultdict(int)
        row_steps_by_zone: dict[int, set[int]] = defaultdict(set)
        for student_id in student_ids:
            seat_id = seating_assignments_by_student[student_id]
            zone_id = topology.local_zone_id_by_seat[seat_id]
            zone_counts[zone_id] += 1
            row_steps_by_zone[zone_id].add(topology.y_step_by_seat[seat_id])
        primary_zone_id = min(
            zone_counts, key=lambda zone_id: (-zone_counts[zone_id], zone_id), default=0
        )
        primary_zone_size = zone_counts.get(primary_zone_id, 0)
        secondary_zone_student_count += max(len(student_ids) - primary_zone_size, 0)
        primary_zone_rows = sorted(row_steps_by_zone.get(primary_zone_id, set()))
        if primary_zone_rows:
            primary_zone_row_gap_count += (
                primary_zone_rows[-1] - primary_zone_rows[0] + 1 - len(primary_zone_rows)
            )
    return secondary_zone_student_count, primary_zone_row_gap_count


def _trial_seed(*, scenario_key: str, candidate_key: str, trial_index: int) -> int:
    text = f"{scenario_key}:{candidate_key}:{trial_index}"
    return sum((index + 1) * ord(char) for index, char in enumerate(text))


def _trial_rule_valid(trial: TrialReport) -> bool:
    return trial.keep_near_valid is not False and trial.keep_apart_valid is not False


def _rule_rate(*, trials: tuple[TrialReport, ...], attr_name: str, enabled: bool) -> float | None:
    if not enabled:
        return None
    return sum(1.0 for trial in trials if getattr(trial, attr_name) is True) / len(trials)


def _live_seating_input(
    *,
    scenario: ScenarioDefinition,
    use_compactness: bool,
) -> LiveSeatingContinuityInput | None:
    if not use_compactness:
        return None
    return LiveSeatingContinuityInput(
        room_context=grouping_support.build_room_context(template=scenario.template),
        seat_assignments=[
            SeatAssignment(student_id=student_id, seat_id=seat_id)
            for student_id, seat_id in sorted(scenario.seating_assignments_by_student.items())
        ],
    )
