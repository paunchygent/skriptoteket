"""Scoring and helper utilities for smart grouping.

Purpose:
    Keep smart-grouping scoring, static-context assembly, and greedy-order
    generation separate from the main solver orchestration.

Relationships:
    - consumed by `smart_grouping.py`
    - reuses topology and history helpers from `smart_grouping_scoring.py`
    - re-exported through `smart_grouping.py` for the current import surface
"""

from __future__ import annotations

from itertools import combinations
from math import inf
from random import Random

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    GroupAssignment,
    RelationshipKind,
    RosterSmartRules,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_scoring import (
    build_live_seating_topology,
    group_center_distance_cost,
    group_topology_cohesion,
    history_coassignment_counts,
    normalized_partition_signature,
    normalized_size_deviation,
    seat_topology_pair_distances,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_types import (
    ClassroomCompactnessConfig,
    GreedySearchConfig,
    LiveSeatingContinuityInput,
    _CandidateScore,
    _StaticScoringContext,
)

KEEP_NEAR_PAIR_REWARD = 8.0
KEEP_NEAR_PAIR_SPLIT_PENALTY = 8.0
KEEP_APART_PAIR_REWARD = 2.0
KEEP_APART_PAIR_COLLISION_PENALTY = 1_000.0
GROUPING_HISTORY_PAIR_REPEAT_PENALTY = 5.0
SIZE_DEVIATION_PENALTY = 1.5


def build_static_scoring_context(
    *,
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> _StaticScoringContext:
    """Build the shared run-level scoring context once per solver invocation."""

    current_mapping = {
        assignment.student_id: assignment.group_id for assignment in current_group_assignments
    }
    seating_assignments_by_student = (
        {
            assignment.student_id: assignment.seat_id
            for assignment in live_seating_continuity.seat_assignments
        }
        if live_seating_continuity is not None
        else {}
    )
    topology = (
        build_live_seating_topology(room_context=live_seating_continuity.room_context)
        if live_seating_continuity is not None
        else None
    )
    seat_pair_distances = (
        seat_topology_pair_distances(
            topology=topology,
            seat_assignments_by_student=seating_assignments_by_student,
        )
        if topology is not None
        else {}
    )
    return _StaticScoringContext(
        keep_near_clusters=tuple(
            tuple(sorted(rule.student_ids))
            for rule in smart_rules.relationship_rules
            if rule.kind is RelationshipKind.KEEP_NEAR
        ),
        keep_apart_clusters=tuple(
            tuple(sorted(rule.student_ids))
            for rule in smart_rules.relationship_rules
            if rule.kind is RelationshipKind.KEEP_APART
        ),
        history_repeat_counts=history_coassignment_counts(history_checkpoints),
        current_partition_signature=(
            normalized_partition_signature(current_mapping) if current_mapping else None
        ),
        seating_assignments_by_student=seating_assignments_by_student,
        topology=topology,
        seat_pair_distances=seat_pair_distances,
    )


def score_candidate(
    *,
    assignments_by_student: dict[str, str],
    group_ids: tuple[str, ...],
    total_student_count: int,
    static_context: _StaticScoringContext,
    classroom_compactness_config: ClassroomCompactnessConfig,
) -> _CandidateScore:
    """Score one grouping candidate lexicographically across the active lanes."""

    if not group_size_distribution_is_feasible(
        assignments_by_student=assignments_by_student,
        group_ids=group_ids,
        total_student_count=total_student_count,
    ):
        return invalid_candidate_score()

    explicit_rules, explicit_tradeoff = _explicit_rule_score(
        assignments_by_student=assignments_by_student,
        keep_near_clusters=static_context.keep_near_clusters,
        keep_apart_clusters=static_context.keep_apart_clusters,
    )
    classroom_compactness = _classroom_compactness_score(
        assignments_by_student=assignments_by_student,
        static_context=static_context,
        config=classroom_compactness_config,
    )
    history = _history_score(
        assignments_by_student=assignments_by_student,
        history_repeat_counts=static_context.history_repeat_counts,
    )
    size_balance = -SIZE_DEVIATION_PENALTY * normalized_size_deviation(
        assignments_by_student=assignments_by_student,
        group_ids=group_ids,
    )
    diversity = _diversity_score(
        assignments_by_student=assignments_by_student,
        current_partition_signature=static_context.current_partition_signature,
    )
    return _CandidateScore(
        explicit_rules=explicit_rules,
        classroom_compactness=classroom_compactness,
        history=history,
        size_balance=size_balance,
        diversity=diversity,
        has_tradeoffs=explicit_tradeoff,
    )


def greedy_student_orders(
    *,
    student_ids: tuple[str, ...],
    static_context: _StaticScoringContext,
    greedy_search_config: GreedySearchConfig,
) -> tuple[tuple[str, ...], ...]:
    """Return a small set of rule-aware greedy orderings to compare."""

    keep_apart_degree = {student_id: 0 for student_id in student_ids}
    keep_near_degree = {student_id: 0 for student_id in student_ids}
    for cluster in static_context.keep_apart_clusters:
        _add_cluster_degree(cluster=cluster, degree_by_student=keep_apart_degree)
    for cluster in static_context.keep_near_clusters:
        _add_cluster_degree(cluster=cluster, degree_by_student=keep_near_degree)

    original_order = tuple(student_ids)
    keep_apart_first = tuple(
        sorted(
            student_ids,
            key=lambda student_id: (
                -keep_apart_degree[student_id],
                -keep_near_degree[student_id],
                student_id,
            ),
        )
    )
    keep_near_first = tuple(
        sorted(
            student_ids,
            key=lambda student_id: (
                -keep_near_degree[student_id],
                -keep_apart_degree[student_id],
                student_id,
            ),
        )
    )
    unique_orders: list[tuple[str, ...]] = []
    for order in (original_order, keep_apart_first, keep_near_first):
        if order not in unique_orders:
            unique_orders.append(order)
    if greedy_search_config.randomized_order_attempts > 0:
        randomizer = Random(greedy_search_config.random_seed)
        shuffled_student_ids = list(student_ids)
        for _ in range(greedy_search_config.randomized_order_attempts):
            randomizer.shuffle(shuffled_student_ids)
            shuffled_order = tuple(shuffled_student_ids)
            if shuffled_order not in unique_orders:
                unique_orders.append(shuffled_order)
    return tuple(unique_orders)


def classroom_compactness_pair_score(
    step_distance: int,
    *,
    config: ClassroomCompactnessConfig,
) -> float:
    """Score one same-group seated pair using an elastic quadratic spread cost."""

    within_radius_bonus = max(config.elastic_radius - step_distance + 1, 0)
    overflow_distance = max(step_distance - config.elastic_radius, 0)
    return config.proximity_reward * float(within_radius_bonus) - config.distance_penalty * float(
        overflow_distance**2
    )


def group_size_distribution_is_feasible(
    *,
    assignments_by_student: dict[str, str],
    group_ids: tuple[str, ...],
    total_student_count: int,
) -> bool:
    """Return whether the candidate can still end in one valid ±1 size distribution."""

    counts = {group_id: 0 for group_id in group_ids}
    for group_id in assignments_by_student.values():
        counts[group_id] += 1
    lower, upper = group_size_bounds(
        total_student_count=total_student_count,
        group_count=len(group_ids),
    )
    if any(count > upper for count in counts.values()):
        return False
    remaining_students = total_student_count - len(assignments_by_student)
    required_to_reach_lower = sum(max(lower - count, 0) for count in counts.values())
    return required_to_reach_lower <= remaining_students


def group_size_bounds(*, total_student_count: int, group_count: int) -> tuple[int, int]:
    """Return the only valid final lower/upper group sizes for the current draft."""

    if group_count <= 0:
        return (0, 0)
    lower = total_student_count // group_count
    upper = lower + (1 if total_student_count % group_count else 0)
    return (lower, upper)


def invalid_candidate_score() -> _CandidateScore:
    """Return one sentinel score for candidates that violate hard invariants."""

    return _CandidateScore(
        explicit_rules=-inf,
        classroom_compactness=-inf,
        history=-inf,
        size_balance=-inf,
        diversity=-inf,
        has_tradeoffs=True,
    )


def _explicit_rule_score(
    *,
    assignments_by_student: dict[str, str],
    keep_near_clusters: tuple[tuple[str, ...], ...],
    keep_apart_clusters: tuple[tuple[str, ...], ...],
) -> tuple[float, bool]:
    explicit_rules = 0.0
    explicit_tradeoff = False
    for cluster in keep_near_clusters:
        for left_id, right_id in combinations(cluster, 2):
            if left_id not in assignments_by_student or right_id not in assignments_by_student:
                continue
            if assignments_by_student[left_id] == assignments_by_student[right_id]:
                explicit_rules += KEEP_NEAR_PAIR_REWARD
            else:
                explicit_rules -= KEEP_NEAR_PAIR_SPLIT_PENALTY
                explicit_tradeoff = True
    for cluster in keep_apart_clusters:
        for left_id, right_id in combinations(cluster, 2):
            if left_id not in assignments_by_student or right_id not in assignments_by_student:
                continue
            if assignments_by_student[left_id] != assignments_by_student[right_id]:
                explicit_rules += KEEP_APART_PAIR_REWARD
            else:
                explicit_rules -= KEEP_APART_PAIR_COLLISION_PENALTY
                explicit_tradeoff = True
    return explicit_rules, explicit_tradeoff


def _classroom_compactness_score(
    *,
    assignments_by_student: dict[str, str],
    static_context: _StaticScoringContext,
    config: ClassroomCompactnessConfig,
) -> float:
    classroom_compactness = 0.0
    for pair, step_distance in static_context.seat_pair_distances.items():
        left_id, right_id = tuple(pair)
        if left_id not in assignments_by_student or right_id not in assignments_by_student:
            continue
        if assignments_by_student[left_id] == assignments_by_student[right_id]:
            classroom_compactness += classroom_compactness_pair_score(
                step_distance,
                config=config,
            )
    if config.center_distance_penalty > 0.0:
        classroom_compactness -= config.center_distance_penalty * group_center_distance_cost(
            assignments_by_student=assignments_by_student,
            seat_assignments_by_student=static_context.seating_assignments_by_student,
            pair_distances=static_context.seat_pair_distances,
            elastic_radius=config.elastic_radius,
        )
    if static_context.topology is None:
        return classroom_compactness
    for group_metrics in group_topology_cohesion(
        assignments_by_student=assignments_by_student,
        seat_assignments_by_student=static_context.seating_assignments_by_student,
        topology=static_context.topology,
    ).values():
        classroom_compactness -= config.disconnected_component_penalty * max(
            group_metrics.component_count - 1, 0
        )
        classroom_compactness -= (
            config.singleton_component_penalty * group_metrics.singleton_component_count
        )
        classroom_compactness -= config.nearest_component_penalty * float(
            group_metrics.secondary_component_gap_cost
        )
        classroom_compactness -= config.split_block_penalty * max(group_metrics.block_count - 1, 0)
        classroom_compactness -= config.secondary_block_penalty * float(
            group_metrics.secondary_block_student_cost
        )
        classroom_compactness -= config.secondary_zone_penalty * float(
            group_metrics.secondary_zone_student_cost
        )
        classroom_compactness -= config.zone_row_gap_penalty * float(
            group_metrics.primary_zone_row_gap_cost
        )
    return classroom_compactness


def _history_score(
    *,
    assignments_by_student: dict[str, str],
    history_repeat_counts: dict[frozenset[str], int],
) -> float:
    history = 0.0
    for pair, repeat_count in history_repeat_counts.items():
        left_id, right_id = tuple(pair)
        if left_id not in assignments_by_student or right_id not in assignments_by_student:
            continue
        if assignments_by_student[left_id] == assignments_by_student[right_id]:
            history -= GROUPING_HISTORY_PAIR_REPEAT_PENALTY * repeat_count
    return history


def _diversity_score(
    *,
    assignments_by_student: dict[str, str],
    current_partition_signature: tuple[tuple[str, ...], ...] | None,
) -> float:
    if current_partition_signature is None:
        return 0.0
    return (
        1.0
        if normalized_partition_signature(assignments_by_student) != current_partition_signature
        else 0.0
    )


def _add_cluster_degree(
    *,
    cluster: tuple[str, ...],
    degree_by_student: dict[str, int],
) -> None:
    cluster_weight = max(len(cluster) - 1, 0)
    for student_id in cluster:
        if student_id in degree_by_student:
            degree_by_student[student_id] += cluster_weight
