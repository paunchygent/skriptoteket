"""History-backed diversity scoring for Klassrumskartan smart seating.

Purpose:
    Convert accepted seating history summaries into anti-repeat score terms
    for whole layouts, students, and relationship rule groups.

Relationships:
    - Consumes diversity counts built from export checkpoints.
    - Supplies focused scoring helpers to the candidate scorer.
"""

from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_history import (
    normalized_layout_signature,
)

if TYPE_CHECKING:
    from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
        SeatScoreContext,
    )

HISTORY_LAYOUT_REPEAT_PENALTY = 28.0
HISTORY_STUDENT_SEAT_REPEAT_PENALTY = 3.8
HISTORY_STUDENT_BLOCK_REPEAT_PENALTY = 1.35
HISTORY_STUDENT_ZONE_REPEAT_PENALTY = 0.9
HISTORY_STUDENT_FRONT_RANK_REPEAT_PENALTY = 0.45
HISTORY_KEEP_NEAR_SEAT_REPEAT_PENALTY = 7.0
HISTORY_KEEP_NEAR_MODE_REPEAT_PENALTY = 1.4
HISTORY_KEEP_APART_SEAT_REPEAT_PENALTY = 14.0
HISTORY_KEEP_APART_BLOCK_REPEAT_PENALTY = 3.0
HISTORY_KEEP_APART_ZONE_REPEAT_PENALTY = 2.0


def history_diversity_score(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> float:
    """Score complete-candidate history diversity."""

    if not context.history_diversity.has_checkpoints:
        return 0.0
    score = _layout_history_diversity_score(mapping=mapping, context=context)
    for student_id, seat_id in mapping.items():
        score += student_history_diversity_score(
            student_id=student_id,
            seat_id=seat_id,
            context=context,
            weight_multiplier=1.0,
        )
    score += _keep_near_history_diversity_score(mapping=mapping, context=context)
    score += _keep_apart_history_diversity_score(mapping=mapping, context=context)
    return score


def student_history_diversity_score(
    *,
    student_id: str,
    seat_id: str,
    context: SeatScoreContext,
    weight_multiplier: float,
) -> float:
    """Score one student's checkpoint-backed seat, block, zone, and rank reuse."""

    if (
        not context.history_diversity.has_checkpoints
        or student_id in context.fixed_assignments_by_student
    ):
        return 0.0
    block_id = context.topology.block_id_by_seat[seat_id]
    zone_id = context.topology.local_zone_id_by_seat[seat_id]
    front_rank = context.topology.front_rank_by_seat[seat_id]
    score = 0.0
    score -= (
        context.history_diversity.seat_counts_by_student.get(student_id, {}).get(seat_id, 0)
        * HISTORY_STUDENT_SEAT_REPEAT_PENALTY
    )
    score -= (
        context.history_diversity.block_counts_by_student.get(student_id, {}).get(block_id, 0)
        * HISTORY_STUDENT_BLOCK_REPEAT_PENALTY
    )
    score -= (
        context.history_diversity.zone_counts_by_student.get(student_id, {}).get(zone_id, 0)
        * HISTORY_STUDENT_ZONE_REPEAT_PENALTY
    )
    score -= (
        context.history_diversity.front_rank_counts_by_student.get(student_id, {}).get(
            front_rank,
            0,
        )
        * HISTORY_STUDENT_FRONT_RANK_REPEAT_PENALTY
    )
    return score * weight_multiplier * context.history_diversity_weight


def keep_apart_pair_history_diversity_score(
    *,
    pair_key: frozenset[str],
    pair_seat_ids: frozenset[str],
    context: SeatScoreContext,
    weight_multiplier: float,
) -> float:
    """Score unordered keep-apart seat-pair reuse without counting swaps as unique."""

    if not context.history_diversity.has_checkpoints:
        return 0.0
    repeat_count = context.history_diversity.keep_apart_pair_seat_counts.get(
        pair_key,
        {},
    ).get(pair_seat_ids, 0)
    return (
        -repeat_count
        * HISTORY_KEEP_APART_SEAT_REPEAT_PENALTY
        * context.history_diversity_weight
        * weight_multiplier
    )


def _layout_history_diversity_score(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> float:
    return (
        -context.history_diversity.layout_counts.get(
            normalized_layout_signature(
                mapping,
                fixed_student_ids=set(context.fixed_assignments_by_student),
            ),
            0,
        )
        * HISTORY_LAYOUT_REPEAT_PENALTY
        * context.history_diversity_weight
    )


def _keep_near_history_diversity_score(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> float:
    score = 0.0
    for cluster in context.keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            pair_key = frozenset((left_id, right_id))
            pair_seat_ids = frozenset((left_seat_id, right_seat_id))
            score -= (
                context.history_diversity.keep_near_pair_seat_counts.get(pair_key, {}).get(
                    pair_seat_ids,
                    0,
                )
                * HISTORY_KEEP_NEAR_SEAT_REPEAT_PENALTY
            )
            relation_mode = context.topology.pair(
                left_seat_id,
                right_seat_id,
            ).keep_near_relation_mode
            if relation_mode is None:
                continue
            score -= (
                context.history_diversity.keep_near_pair_mode_counts.get(pair_key, {}).get(
                    relation_mode,
                    0,
                )
                * HISTORY_KEEP_NEAR_MODE_REPEAT_PENALTY
            )
    return score * context.history_diversity_weight


def _keep_apart_history_diversity_score(
    *,
    mapping: dict[str, str],
    context: SeatScoreContext,
) -> float:
    pair_score = 0.0
    signature_score = 0.0
    for cluster in context.keep_apart_clusters:
        cluster_key = frozenset(cluster)
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            pair_score += keep_apart_pair_history_diversity_score(
                pair_key=frozenset((left_id, right_id)),
                pair_seat_ids=frozenset((left_seat_id, right_seat_id)),
                context=context,
                weight_multiplier=1.0,
            )
        block_signature = _cluster_signature(
            mapping=mapping,
            cluster=cluster,
            context=context,
            signature_kind="block",
        )
        zone_signature = _cluster_signature(
            mapping=mapping,
            cluster=cluster,
            context=context,
            signature_kind="zone",
        )
        signature_score -= (
            context.history_diversity.keep_apart_block_signature_counts.get(
                cluster_key,
                {},
            ).get(block_signature, 0)
            * HISTORY_KEEP_APART_BLOCK_REPEAT_PENALTY
        )
        signature_score -= (
            context.history_diversity.keep_apart_zone_signature_counts.get(
                cluster_key,
                {},
            ).get(zone_signature, 0)
            * HISTORY_KEEP_APART_ZONE_REPEAT_PENALTY
        )
    return pair_score + signature_score * context.history_diversity_weight


def _cluster_signature(
    *,
    mapping: dict[str, str],
    cluster: set[str],
    context: SeatScoreContext,
    signature_kind: str,
) -> tuple[int, ...]:
    values: list[int] = []
    for student_id in cluster:
        seat_id = mapping.get(student_id)
        if seat_id is None:
            continue
        if signature_kind == "block":
            values.append(context.topology.block_id_by_seat[seat_id])
            continue
        values.append(context.topology.local_zone_id_by_seat[seat_id])
    if len(values) < 2:
        return ()
    return tuple(sorted(values))
