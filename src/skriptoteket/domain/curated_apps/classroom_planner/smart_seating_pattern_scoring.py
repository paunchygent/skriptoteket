"""Rule-pattern rotation scoring for Klassrumskartan smart seating.

Purpose:
    Score teacher-visible rule-group movement without treating student swaps
    inside the same pair seats as distinct patterns.

Relationships:
    - Uses seat topology from the smart-seating domain layer.
    - Supplies compact helpers to the candidate scorer and solver context
      builder so current-draft reruns can rotate rule groups deterministically.
"""

from __future__ import annotations

from hashlib import blake2b
from itertools import combinations
from math import gcd

from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    SeatTopology,
)

CURRENT_BLOCK_PATTERN_REPEAT_PENALTY = 96.0
CURRENT_BLOCK_PATTERN_TARGET_BONUS = 144.0
CURRENT_BLOCK_PATTERN_FRESH_BONUS = 18.0


def block_signature_for_students(
    *,
    assignments_by_student: dict[str, str],
    student_ids: set[str] | frozenset[str],
    topology: SeatTopology,
) -> tuple[int, ...]:
    """Return an unordered block signature for one rule group."""

    values = [
        topology.block_id_by_seat[assignments_by_student[student_id]]
        for student_id in student_ids
        if student_id in assignments_by_student
    ]
    if len(values) < len(student_ids):
        return ()
    return tuple(sorted(values))


def current_keep_near_block_signatures(
    *,
    keep_near_clusters: list[set[str]],
    current_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[frozenset[str], tuple[int, ...]]:
    """Capture unordered block signatures for current keep-near pairs."""

    return _current_pair_signatures(
        clusters=keep_near_clusters,
        current_assignments_by_student=current_assignments_by_student,
        topology=topology,
    )


def current_keep_apart_block_signatures(
    *,
    keep_apart_clusters: list[set[str]],
    current_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[frozenset[str], tuple[int, ...]]:
    """Capture unordered block signatures for current keep-apart pairs."""

    return _current_pair_signatures(
        clusters=[cluster for cluster in keep_apart_clusters if len(cluster) == 2],
        current_assignments_by_student=current_assignments_by_student,
        topology=topology,
    )


def current_block_rotation_score(
    *,
    pair_key: frozenset[str],
    candidate_signature: tuple[int, ...],
    current_signatures_by_pair: dict[frozenset[str], tuple[int, ...]],
    block_ids: tuple[int, ...],
) -> float:
    """Score current-draft rule movement by unordered block pattern."""

    current_signature = current_signatures_by_pair.get(pair_key)
    if not current_signature or not block_ids or not candidate_signature:
        return 0.0
    if candidate_signature == current_signature:
        return -CURRENT_BLOCK_PATTERN_REPEAT_PENALTY
    target_signature = _rotated_signature(
        signature=current_signature,
        block_ids=block_ids,
        pair_key=pair_key,
    )
    if candidate_signature == target_signature:
        return CURRENT_BLOCK_PATTERN_TARGET_BONUS
    if set(candidate_signature) & set(current_signature):
        return 0.0
    return CURRENT_BLOCK_PATTERN_FRESH_BONUS


def _current_pair_signatures(
    *,
    clusters: list[set[str]],
    current_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[frozenset[str], tuple[int, ...]]:
    signatures_by_pair: dict[frozenset[str], tuple[int, ...]] = {}
    for cluster in clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            pair_key = frozenset((left_id, right_id))
            signature = block_signature_for_students(
                assignments_by_student=current_assignments_by_student,
                student_ids=pair_key,
                topology=topology,
            )
            if signature:
                signatures_by_pair[pair_key] = signature
    return signatures_by_pair


def _rotated_signature(
    *,
    signature: tuple[int, ...],
    block_ids: tuple[int, ...],
    pair_key: frozenset[str],
) -> tuple[int, ...]:
    index_by_block_id = {block_id: index for index, block_id in enumerate(block_ids)}
    current_blocks = set(signature)
    fallback: tuple[int, ...] = ()
    for step in _rotation_steps(pair_key=pair_key, block_count=len(block_ids)):
        rotated_values = []
        for block_id in signature:
            current_index = index_by_block_id.get(block_id)
            if current_index is None:
                return ()
            rotated_values.append(block_ids[(current_index + step) % len(block_ids)])
        rotated_signature = tuple(sorted(rotated_values))
        if not fallback:
            fallback = rotated_signature
        if set(rotated_signature).isdisjoint(current_blocks):
            return rotated_signature
    return fallback


def _rotation_steps(*, pair_key: frozenset[str], block_count: int) -> tuple[int, ...]:
    if block_count <= 1:
        return (1,)
    candidates = [
        step for step in (4, 5, 3, 2, 1) if step < block_count and gcd(step, block_count) == 1
    ]
    if not candidates:
        return (1,)
    digest = blake2b("|".join(sorted(pair_key)).encode("utf-8"), digest_size=1).digest()[0]
    offset = digest % len(candidates)
    return tuple(candidates[offset:] + candidates[:offset])
