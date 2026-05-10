"""Rotation-aware scoring helpers for smart seating.

This module keeps the smart-seating rule semantics explicit while preserving a
small core solver module. It owns near-teacher pool rotation and keep-near
local relation rotation without introducing a generic optimization framework.
"""

from __future__ import annotations

from hashlib import blake2b
from itertools import combinations
from math import gcd

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_support_context import (
    SeatingContext,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    KeepNearRelationMode,
    SeatPairTopology,
    SeatTopology,
)

_KEEP_NEAR_ROTATION_CYCLE: tuple[KeepNearRelationMode, ...] = (
    "adjacent-row",
    "diagonal-block",
    "adjacent-column",
)


def near_teacher_history_counts(
    *,
    history_checkpoints: list[SeatingExportCheckpoint],
    pool_seat_ids: set[str],
) -> dict[str, dict[str, int]]:
    """Count near-teacher pool seat reuse from export-backed history."""

    counts_by_student: dict[str, dict[str, int]] = {}
    for checkpoint in history_checkpoints:
        for placement in checkpoint.seating_snapshot.placed_assignments:
            if placement.seat_id not in pool_seat_ids:
                continue
            seat_counts = counts_by_student.setdefault(placement.student_id, {})
            seat_counts[placement.seat_id] = seat_counts.get(placement.seat_id, 0) + 1
    return counts_by_student


def current_keep_near_modes(
    *,
    keep_near_clusters: list[set[str]],
    current_assignments_by_student: dict[str, str],
    topology: SeatTopology,
) -> dict[frozenset[str], KeepNearRelationMode]:
    """Capture the current keep-near local relation mode for each active pair."""

    modes_by_pair: dict[frozenset[str], KeepNearRelationMode] = {}
    for cluster in keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = current_assignments_by_student.get(left_id)
            right_seat_id = current_assignments_by_student.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            mode = topology.pair(left_seat_id, right_seat_id).keep_near_relation_mode
            if mode is not None:
                modes_by_pair[frozenset((left_id, right_id))] = mode
    return modes_by_pair


def current_keep_near_pair_seat_ids(
    *,
    keep_near_clusters: list[set[str]],
    current_assignments_by_student: dict[str, str],
) -> dict[frozenset[str], frozenset[str]]:
    """Capture the current seat ids for each active keep-near pair."""

    seat_ids_by_pair: dict[frozenset[str], frozenset[str]] = {}
    for cluster in keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = current_assignments_by_student.get(left_id)
            right_seat_id = current_assignments_by_student.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                continue
            seat_ids_by_pair[frozenset((left_id, right_id))] = frozenset(
                (left_seat_id, right_seat_id)
            )
    return seat_ids_by_pair


def near_teacher_score(
    *,
    student_id: str,
    seat_id: str,
    topology: SeatTopology,
    near_teacher_student_count: int,
    pool_rank_by_seat: dict[str, int],
    history_counts_by_student: dict[str, dict[str, int]],
    current_pool_seat_ids: set[str],
    current_assignments_by_student: dict[str, str],
) -> float:
    """Score one seat for a near-teacher student inside the valid teacher pool."""

    pool_rank = pool_rank_by_seat.get(seat_id)
    if pool_rank is None:
        return (
            -18.0
            + (1.0 - topology.normalized_front_distance(seat_id)) * 4.0
            + (1.0 - topology.normalized_lateral_distance(seat_id)) * 2.0
        )
    student_history = history_counts_by_student.get(student_id, {})
    score = 24.0
    score += (1.0 - topology.normalized_front_distance(seat_id)) * 5.5
    score += (1.0 - topology.normalized_lateral_distance(seat_id)) * 3.0
    score -= float(pool_rank) * 0.15
    score -= student_history.get(seat_id, 0) * 1.0
    score -= (
        sum(
            count
            for previous_seat_id, count in student_history.items()
            if topology.block_id_by_seat.get(previous_seat_id) == topology.block_id_by_seat[seat_id]
        )
        * 0.45
    )
    score -= (
        sum(
            count
            for previous_seat_id, count in student_history.items()
            if topology.front_rank_by_seat.get(previous_seat_id)
            == topology.front_rank_by_seat[seat_id]
        )
        * 0.2
    )
    if seat_id in current_pool_seat_ids:
        score -= 1.0
    current_seat_id = current_assignments_by_student.get(student_id)
    if current_seat_id is None:
        return score
    score -= (1.0 - topology.normalized_front_distance(seat_id)) * 1.0
    score -= (1.0 - topology.normalized_lateral_distance(seat_id)) * 0.75
    current_pair = topology.pair(current_seat_id, seat_id)
    current_rank = pool_rank_by_seat.get(current_seat_id)
    if current_rank is not None:
        pool_size = len(pool_rank_by_seat)
        target_rank = (
            current_rank
            + _rotation_step(
                student_id=student_id,
                pool_size=pool_size,
                near_teacher_student_count=near_teacher_student_count,
            )
        ) % pool_size
        rank_gap = abs(pool_rank - target_rank)
        circular_gap = min(rank_gap, pool_size - rank_gap)
        score += max(0.0, pool_size / 2 - float(circular_gap)) * 2.2
    if current_seat_id == seat_id:
        score -= 4.5
    if current_pair.same_block:
        score -= 4.0
    if current_pair.front_gap == 0:
        score -= 1.8
    if current_pair.lateral_gap <= 1:
        score -= 1.2
    return score


def keep_near_pair_score(
    *,
    pair: SeatPairTopology,
    cluster_size: int,
    seating_context: SeatingContext = "row_layout",
    current_mode: KeepNearRelationMode | None = None,
    pair_key: frozenset[str] | None = None,
    pair_seat_ids: frozenset[str] | None = None,
    current_pair_seat_ids: frozenset[str] | None = None,
) -> float:
    """Score one compact keep-near relation, including local-mode rotation."""

    if cluster_size == 2:
        if seating_context == "shared_table":
            score = _shared_table_pair_score(pair)
        elif seating_context in {"bench_row", "row_layout"}:
            score = _row_pair_score(pair)
        elif pair.orthogonally_adjacent:
            score = 18.0
        elif pair.same_line_one_step:
            score = 2.5
        elif pair.diagonal_neighbor and pair.same_local_zone:
            score = -4.0
        elif pair.same_row or pair.same_column:
            score = -6.0 - float(pair.grid_manhattan)
        elif pair.same_local_zone and pair.grid_manhattan <= 3:
            score = -8.0
        elif pair.same_local_zone:
            score = -10.0
        else:
            score = -12.0
    else:
        if pair.orthogonally_adjacent:
            score = 16.0
        elif pair.diagonal_neighbor and pair.same_local_zone:
            score = 14.5
        elif pair.same_line_one_step:
            score = 12.5
        elif pair.same_row or pair.same_column:
            score = 2.0 - pair.grid_manhattan * 3.0
        elif pair.same_local_zone and pair.grid_manhattan <= 3:
            score = -2.0
        elif pair.same_local_zone:
            score = -6.0
        else:
            score = -10.0
    next_modes = _next_keep_near_modes(
        cluster_size=cluster_size,
        current_mode=current_mode,
        pair_key=pair_key,
        current_pair_seat_ids=current_pair_seat_ids,
    )
    normalized_mode = _normalized_keep_near_mode(pair.keep_near_relation_mode)
    normalized_current_mode = _normalized_keep_near_mode(current_mode)
    if pair.keep_near_relation_mode is not None and pair.keep_near_relation_mode == current_mode:
        score -= 3.5
    elif normalized_mode is not None and normalized_mode == normalized_current_mode:
        score -= 2.0
    if pair_seat_ids is not None and current_pair_seat_ids is not None:
        shared_seat_count = len(pair_seat_ids & current_pair_seat_ids)
        if shared_seat_count == 2:
            score -= 7.0
        elif shared_seat_count == 1:
            score -= 3.5
    if normalized_mode is not None:
        if next_modes and normalized_mode == next_modes[0]:
            score += 6.0
        elif len(next_modes) > 1 and normalized_mode == next_modes[1]:
            score += 1.5
    return score


def _shared_table_pair_score(pair: SeatPairTopology) -> float:
    if pair.keep_near_relation_mode in {"adjacent-row", "adjacent-column"}:
        return 18.0
    if pair.keep_near_relation_mode in {"diagonal-block", "one-step-row", "one-step-column"}:
        return 6.0
    if pair.same_local_zone:
        return -6.0
    return -12.0


def _row_pair_score(pair: SeatPairTopology) -> float:
    if pair.keep_near_relation_mode == "adjacent-row":
        return 22.0
    if pair.keep_near_relation_mode == "adjacent-column":
        return 7.0
    if pair.keep_near_relation_mode in {"diagonal-block", "one-step-row", "one-step-column"}:
        return -4.0
    if pair.same_row or pair.same_column:
        return -6.0 - float(pair.grid_manhattan)
    if pair.same_local_zone and pair.grid_manhattan <= 3:
        return -8.0
    if pair.same_local_zone:
        return -10.0
    return -12.0


def _rotation_step(
    *,
    student_id: str,
    pool_size: int,
    near_teacher_student_count: int,
) -> int:
    candidates = [
        candidate
        for candidate in (5, 7, 3, 2, 1)
        if candidate < pool_size and gcd(candidate, pool_size) == 1
    ]
    if not candidates:
        return 1
    if near_teacher_student_count <= 1:
        return candidates[0]
    digest = blake2b(student_id.encode("utf-8"), digest_size=1).digest()[0]
    offset = candidates[digest % len(candidates)]
    return offset if digest % 2 == 0 else -offset


def _normalized_keep_near_mode(
    mode: KeepNearRelationMode | None,
) -> KeepNearRelationMode | None:
    if mode == "one-step-row":
        return "adjacent-row"
    if mode == "one-step-column":
        return "adjacent-column"
    if mode in _KEEP_NEAR_ROTATION_CYCLE:
        return mode
    return None


def _next_keep_near_modes(
    *,
    cluster_size: int,
    current_mode: KeepNearRelationMode | None,
    pair_key: frozenset[str] | None,
    current_pair_seat_ids: frozenset[str] | None,
) -> tuple[KeepNearRelationMode, ...]:
    normalized_mode = _normalized_keep_near_mode(current_mode)
    if normalized_mode is None or pair_key is None:
        return ()
    if cluster_size == 2:
        if normalized_mode == "adjacent-row":
            return ("adjacent-column",)
        if normalized_mode == "adjacent-column":
            return ("adjacent-row",)
        seed_parts = sorted(current_pair_seat_ids or pair_key)
        digest = blake2b("|".join(seed_parts).encode("utf-8"), digest_size=1).digest()[0]
        if digest % 2 == 0:
            return ("adjacent-row", "adjacent-column")
        return ("adjacent-column", "adjacent-row")
    if normalized_mode == "adjacent-row":
        return ("diagonal-block",)
    if normalized_mode == "adjacent-column":
        return ("diagonal-block",)
    seed_parts = sorted(current_pair_seat_ids or pair_key)
    digest = blake2b("|".join(seed_parts).encode("utf-8"), digest_size=1).digest()[0]
    if digest % 2 == 0:
        return ("adjacent-row", "adjacent-column")
    return ("adjacent-column", "adjacent-row")
