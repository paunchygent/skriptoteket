"""Scoring helpers for smart grouping.

Purpose:
    Keep label-insensitive grouping-history math and seating-continuity pair
    extraction separate from the main smart-grouping search module.

Relationships:
    - consumed by `smart_grouping.py`
    - shared by future grouping-history persistence and smart-grouping tests
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from math import inf

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import Seat


def history_coassignment_counts(
    history_checkpoints: list[GroupingExportCheckpoint],
) -> dict[frozenset[str], int]:
    """Count how often each student pair has appeared in the same history group."""

    pair_counts: dict[frozenset[str], int] = defaultdict(int)
    for checkpoint in history_checkpoints:
        for group in checkpoint.grouping_snapshot.groups:
            for left_id, right_id in combinations(sorted(group.student_ids), 2):
                pair_counts[frozenset({left_id, right_id})] += 1
    return dict(pair_counts)


def live_seating_pair_weights(
    *,
    seats: list[Seat],
    seat_assignments_by_student: dict[str, str],
) -> dict[frozenset[str], float]:
    """Score directly adjacent seated pairs as live grouping continuity hints."""

    seat_by_id = {seat.id: seat for seat in seats}
    x_rank = _axis_ranks([seat.x for seat in seats])
    y_rank = _axis_ranks([seat.y for seat in seats])

    pair_weights: dict[frozenset[str], float] = {}
    for left_id, right_id in combinations(sorted(seat_assignments_by_student), 2):
        left_seat = seat_by_id.get(seat_assignments_by_student[left_id])
        right_seat = seat_by_id.get(seat_assignments_by_student[right_id])
        if left_seat is None or right_seat is None:
            continue
        step_distance = abs(x_rank[left_seat.x] - x_rank[right_seat.x]) + abs(
            y_rank[left_seat.y] - y_rank[right_seat.y]
        )
        if step_distance != 1:
            continue
        pair_weights[frozenset({left_id, right_id})] = 1.0
    return pair_weights


def normalized_partition_signature(
    assignments_by_student: dict[str, str],
) -> tuple[tuple[str, ...], ...]:
    """Return one label-insensitive partition signature for repeat detection."""

    groups: dict[str, list[str]] = defaultdict(list)
    for student_id, group_id in assignments_by_student.items():
        groups[group_id].append(student_id)
    normalized_groups = [tuple(sorted(student_ids)) for student_ids in groups.values()]
    return tuple(sorted(normalized_groups, key=lambda group: (len(group), group)))


def normalized_size_deviation(
    *,
    assignments_by_student: dict[str, str],
    group_ids: tuple[str, ...],
) -> float:
    """Return the total deviation from the most even feasible group distribution."""

    counts = {group_id: 0 for group_id in group_ids}
    for group_id in assignments_by_student.values():
        counts[group_id] += 1
    student_count = len(assignments_by_student)
    group_count = len(group_ids)
    if group_count <= 0:
        return inf
    lower = student_count // group_count
    upper = lower + (1 if student_count % group_count else 0)
    return float(sum(min(abs(count - lower), abs(count - upper)) for count in counts.values()))


def _axis_ranks(values: list[int]) -> dict[int, int]:
    ordered_values = sorted(set(values))
    return {value: index for index, value in enumerate(ordered_values)}
