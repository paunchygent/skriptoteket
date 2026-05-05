"""Candidate scoring rules for Klassrumskartan smart seating.

Purpose:
    Evaluate near-teacher preferences, relationship rules, history fairness,
    rerun diversity, and fixed-seat peer awareness for one seating candidate.

Relationships:
    - Consumes seat topology and rotation helpers from the classroom-planner
      domain package.
    - Returns score objects used by the smart-seating search strategies.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    KeepNearRelationMode,
    SeatPairTopology,
    SeatTopology,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_scoring import (
    keep_near_pair_score,
    near_teacher_score,
)

QUALITY_EPSILON = 1e-6
CURRENT_SEAT_REPEAT_PENALTY = 3.0
LAYOUT_REPEAT_PENALTY = 2.5


@dataclass(frozen=True)
class SeatScoreContext:
    """Carry immutable scoring inputs shared across candidate evaluations."""

    topology: SeatTopology
    near_teacher_student_ids: set[str]
    near_teacher_student_count: int
    near_teacher_pool_rank_by_seat: dict[str, int]
    near_teacher_history_counts_by_student: dict[str, dict[str, int]]
    current_near_teacher_pool_seat_ids: set[str]
    current_keep_near_mode_by_pair: dict[frozenset[str], KeepNearRelationMode]
    current_keep_near_seat_ids_by_pair: dict[frozenset[str], frozenset[str]]
    history_targets_by_student: dict[str, float]
    keep_near_clusters: list[set[str]]
    keep_apart_clusters: list[set[str]]
    current_assignments_by_student: dict[str, str]
    fixed_assignments_by_student: dict[str, str]


@dataclass(frozen=True)
class CandidateScore:
    """Keep primary quality separate from secondary diversity preference."""

    quality: float
    diversity: float
    has_tradeoffs: bool


def score_partial_seat(
    *,
    student_id: str,
    seat_id: str,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> float:
    """Score one partial student-to-seat choice against assigned peers."""

    seat_distance = context.topology.normalized_teacher_distance(seat_id)
    full_mapping = _merged_candidate_mapping(mapping=mapping, context=context)
    score = _teacher_priority_score(
        student_id=student_id,
        seat_id=seat_id,
        seat_distance=seat_distance,
        context=context,
    )
    for cluster in context.keep_near_clusters:
        if student_id not in cluster:
            continue
        for peer_id in cluster:
            peer_seat_id = full_mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += keep_near_pair_score(
                pair=context.topology.pair(seat_id, peer_seat_id),
                cluster_size=len(cluster),
                current_mode=context.current_keep_near_mode_by_pair.get(
                    frozenset((student_id, peer_id))
                ),
                pair_key=frozenset((student_id, peer_id)),
                pair_seat_ids=frozenset((seat_id, peer_seat_id)),
                current_pair_seat_ids=context.current_keep_near_seat_ids_by_pair.get(
                    frozenset((student_id, peer_id))
                ),
            )
    for cluster in context.keep_apart_clusters:
        if student_id not in cluster:
            continue
        for peer_id in cluster:
            peer_seat_id = full_mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += keep_apart_pair_score(
                pair=context.topology.pair(seat_id, peer_seat_id),
            )
    if context.current_assignments_by_student.get(student_id) == seat_id:
        score -= CURRENT_SEAT_REPEAT_PENALTY
    return score


def score_candidate(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> CandidateScore:
    """Score one complete candidate, merging hard fixed placements first."""

    mapping = _merged_candidate_mapping(mapping=mapping, context=context)
    quality = 0.0
    diversity = 0.0
    has_tradeoffs = False
    for student_id, seat_id in mapping.items():
        seat_distance = context.topology.normalized_teacher_distance(seat_id)
        quality += _teacher_priority_score(
            student_id=student_id,
            seat_id=seat_id,
            seat_distance=seat_distance,
            context=context,
        )
        if context.current_assignments_by_student.get(student_id) == seat_id:
            diversity -= LAYOUT_REPEAT_PENALTY

    for cluster in context.keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                has_tradeoffs = True
                continue
            pair = context.topology.pair(left_seat_id, right_seat_id)
            quality += keep_near_pair_score(
                pair=pair,
                cluster_size=len(cluster),
                current_mode=context.current_keep_near_mode_by_pair.get(
                    frozenset((left_id, right_id))
                ),
                pair_key=frozenset((left_id, right_id)),
                pair_seat_ids=frozenset((left_seat_id, right_seat_id)),
                current_pair_seat_ids=context.current_keep_near_seat_ids_by_pair.get(
                    frozenset((left_id, right_id))
                ),
            )
            if keep_near_has_tradeoff(pair=pair, cluster_size=len(cluster)):
                has_tradeoffs = True

    for cluster in context.keep_apart_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                has_tradeoffs = True
                continue
            pair = context.topology.pair(left_seat_id, right_seat_id)
            quality += keep_apart_pair_score(pair=pair)
            if keep_apart_has_tradeoff(pair):
                has_tradeoffs = True

    return CandidateScore(quality=quality, diversity=diversity, has_tradeoffs=has_tradeoffs)


def is_better_score(*, score: CandidateScore, current_best: CandidateScore | None) -> bool:
    """Return whether a candidate score should replace the current best."""

    if current_best is None:
        return True
    if current_best.has_tradeoffs and not score.has_tradeoffs:
        return True
    if score.has_tradeoffs and not current_best.has_tradeoffs:
        return False
    if score.quality > current_best.quality + QUALITY_EPSILON:
        return True
    if abs(score.quality - current_best.quality) <= QUALITY_EPSILON:
        return score.diversity > current_best.diversity + QUALITY_EPSILON
    return False


def keep_apart_pair_score(*, pair: SeatPairTopology) -> float:
    """Score one keep-apart pair."""

    if _keep_apart_is_hard_negative(pair):
        return -32.0 if pair.orthogonally_adjacent else -28.0
    spread_score = pair.front_gap * 4.0 + pair.lateral_gap * 4.0
    if not pair.same_block:
        return spread_score + 8.0
    if pair.same_row or pair.same_column:
        return spread_score - 2.5
    return spread_score - 1.0


def keep_near_has_tradeoff(*, pair: SeatPairTopology, cluster_size: int) -> bool:
    """Return whether one keep-near pair missed the preferred local relation."""

    if cluster_size == 2:
        return not pair.orthogonally_adjacent
    return pair.keep_near_relation_mode is None


def keep_apart_has_tradeoff(pair: SeatPairTopology) -> bool:
    """Return whether one keep-apart pair still has immediate contact."""

    return _keep_apart_is_hard_negative(pair)


def _merged_candidate_mapping(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> dict[str, str]:
    """Merge hard fixed placements with one candidate mapping."""

    if not context.fixed_assignments_by_student:
        return mapping
    return {**context.fixed_assignments_by_student, **mapping}


def _teacher_priority_score(
    *,
    student_id: str,
    seat_id: str,
    seat_distance: float,
    context: SeatScoreContext,
) -> float:
    if student_id in context.near_teacher_student_ids:
        return near_teacher_score(
            student_id=student_id,
            seat_id=seat_id,
            topology=context.topology,
            near_teacher_student_count=context.near_teacher_student_count,
            pool_rank_by_seat=context.near_teacher_pool_rank_by_seat,
            history_counts_by_student=context.near_teacher_history_counts_by_student,
            current_pool_seat_ids=context.current_near_teacher_pool_seat_ids,
            current_assignments_by_student=context.current_assignments_by_student,
        )
    target_distance = context.history_targets_by_student.get(student_id)
    if target_distance is None:
        return (1.0 - abs(seat_distance - 0.5)) * 0.4
    return (1.0 - abs(seat_distance - target_distance)) * 6.0


def _keep_apart_is_hard_negative(pair: SeatPairTopology) -> bool:
    """Return whether two seats violate the immediate keep-apart buffer."""

    return pair.orthogonally_adjacent or pair.diagonal_neighbor
