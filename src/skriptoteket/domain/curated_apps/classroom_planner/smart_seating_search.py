"""Search strategies for Klassrumskartan smart seating.

Purpose:
    Explore exact and greedy seating assignments while preserving rule-aware
    pair placement for relationship constraints.

Relationships:
    - Consumes candidate scoring from the smart-seating domain scorer.
    - Keeps search mechanics separate from the public solver orchestration.
"""

from __future__ import annotations

from hashlib import blake2b
from itertools import permutations
from random import Random

from skriptoteket.domain.curated_apps.classroom_planner.models import Seat
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    CandidateScore,
    SeatScoreContext,
    is_better_score,
    score_candidate,
    score_partial_seat,
)

QUALITY_EPSILON = 1e-6
EXACT_ASSIGNMENT_LIMIT = 7
RANDOM_ATTEMPTS = 96


def solve_assignment_search(
    *,
    student_ids: list[str],
    seats: list[Seat],
    context: SeatScoreContext,
) -> tuple[dict[str, str], CandidateScore]:
    """Choose a best mapping with exact search for small cases and greedy search otherwise."""

    if len(student_ids) <= EXACT_ASSIGNMENT_LIMIT:
        return _solve_exact(
            student_ids=student_ids,
            seats=seats,
            context=context,
        )
    return _solve_greedy(
        student_ids=student_ids,
        seats=seats,
        context=context,
    )


def _solve_exact(
    *,
    student_ids: list[str],
    seats: list[Seat],
    context: SeatScoreContext,
) -> tuple[dict[str, str], CandidateScore]:
    seat_ids = [seat.id for seat in seats]
    best_mapping: dict[str, str] | None = None
    best_score: CandidateScore | None = None
    for candidate_seat_ids in permutations(seat_ids, len(student_ids)):
        mapping = dict(zip(student_ids, candidate_seat_ids, strict=True))
        score = score_candidate(mapping=mapping, context=context)
        if is_better_score(score=score, current_best=best_score):
            best_mapping = mapping
            best_score = score
    if best_mapping is None or best_score is None:
        return {}, CandidateScore(quality=0.0, diversity=0.0, has_tradeoffs=False)
    return best_mapping, best_score


def _solve_greedy(
    *,
    student_ids: list[str],
    seats: list[Seat],
    context: SeatScoreContext,
) -> tuple[dict[str, str], CandidateScore]:
    seat_ids = [seat.id for seat in seats]
    rng = _search_rng(student_ids=student_ids, context=context)
    best_mapping: dict[str, str] | None = None
    best_score: CandidateScore | None = None

    for attempt_index in range(RANDOM_ATTEMPTS):
        remaining = seat_ids.copy()
        rng.shuffle(remaining)
        assignment_order = _assignment_order(
            student_ids=student_ids,
            context=context,
            rng=rng,
            attempt_index=attempt_index,
        )
        mapping: dict[str, str] = {}
        handled_student_ids: set[str] = set()
        for student_id in assignment_order:
            if student_id in handled_student_ids:
                continue
            if _assign_relationship_pair(
                student_id=student_id,
                mapping=mapping,
                remaining=remaining,
                handled_student_ids=handled_student_ids,
                context=context,
            ):
                continue
            best_seat_id = max(
                remaining,
                key=lambda seat_id: score_partial_seat(
                    student_id=student_id,
                    seat_id=seat_id,
                    mapping=mapping,
                    context=context,
                ),
            )
            mapping[student_id] = best_seat_id
            remaining.remove(best_seat_id)
            handled_student_ids.add(student_id)
        score = score_candidate(mapping=mapping, context=context)
        if is_better_score(score=score, current_best=best_score):
            best_mapping = mapping
            best_score = score

    if best_mapping is None or best_score is None:
        return {}, CandidateScore(quality=0.0, diversity=0.0, has_tradeoffs=False)
    return best_mapping, best_score


def _search_rng(*, student_ids: list[str], context: SeatScoreContext) -> Random:
    seed_material = "|".join(
        [
            *sorted(student_ids),
            *sorted(
                f"{student}:{seat}"
                for student, seat in context.current_assignments_by_student.items()
            ),
            *sorted(
                f"fixed:{student}:{seat}"
                for student, seat in context.fixed_assignments_by_student.items()
            ),
            f"history:{context.history_fingerprint}",
        ]
    ).encode("utf-8")
    return Random(int.from_bytes(blake2b(seed_material, digest_size=8).digest(), "big"))


def _assignment_order(
    *,
    student_ids: list[str],
    context: SeatScoreContext,
    rng: Random,
    attempt_index: int,
) -> list[str]:
    """Keep hard-to-place students early while still allowing rerun diversity."""

    shuffled_ids = student_ids.copy()
    if attempt_index > 0:
        rng.shuffle(shuffled_ids)
    tie_break_by_student = {student_id: index for index, student_id in enumerate(shuffled_ids)}
    keep_near_before_teacher = bool(
        context.current_keep_near_mode_by_pair
    ) and attempt_index % 4 in (1, 2)
    return sorted(
        student_ids,
        key=lambda student_id: (
            -_max_cluster_size(student_id=student_id, clusters=context.keep_apart_clusters),
            -(
                _max_cluster_size(student_id=student_id, clusters=context.keep_near_clusters)
                if keep_near_before_teacher
                else (1 if student_id in context.near_teacher_student_ids else 0)
            ),
            -(
                (1 if student_id in context.near_teacher_student_ids else 0)
                if keep_near_before_teacher
                else _max_cluster_size(student_id=student_id, clusters=context.keep_near_clusters)
            ),
            tie_break_by_student[student_id],
        ),
    )


def _assign_relationship_pair(
    *,
    student_id: str,
    mapping: dict[str, str],
    remaining: list[str],
    handled_student_ids: set[str],
    context: SeatScoreContext,
) -> bool:
    for label, clusters in (
        ("keep-near", context.keep_near_clusters),
        ("keep-apart", context.keep_apart_clusters),
    ):
        pair = _unassigned_rule_pair(
            student_id=student_id,
            mapping=mapping,
            clusters=clusters,
            context=context,
        )
        if pair is None:
            continue
        left_student_id, right_student_id = pair
        left_seat_id, right_seat_id = _best_pair_assignment(
            student_ids=pair,
            remaining_seat_ids=remaining,
            mapping=mapping,
            context=context,
            label=label,
        )
        mapping[left_student_id] = left_seat_id
        mapping[right_student_id] = right_seat_id
        remaining.remove(left_seat_id)
        remaining.remove(right_seat_id)
        handled_student_ids.update(pair)
        return True
    return False


def _max_cluster_size(*, student_id: str, clusters: list[set[str]]) -> int:
    """Return the largest active rule cluster that includes the student."""

    return max((len(cluster) for cluster in clusters if student_id in cluster), default=0)


def _unassigned_rule_pair(
    *,
    student_id: str,
    mapping: dict[str, str],
    clusters: list[set[str]],
    context: SeatScoreContext,
) -> tuple[str, str] | None:
    """Return a two-student rule pair when both seats can be chosen jointly."""

    for cluster in clusters:
        if student_id not in cluster or len(cluster) != 2:
            continue
        left_id, right_id = sorted(cluster)
        assigned_student_ids = set(mapping) | set(context.fixed_assignments_by_student)
        if left_id in assigned_student_ids or right_id in assigned_student_ids:
            return None
        return left_id, right_id
    return None


def _best_pair_assignment(
    *,
    student_ids: tuple[str, str],
    remaining_seat_ids: list[str],
    mapping: dict[str, str],
    context: SeatScoreContext,
    label: str,
) -> tuple[str, str]:
    """Choose the best ordered seat pair for one compact relationship rule."""

    left_student_id, right_student_id = student_ids
    best_pair: tuple[str, str] | None = None
    best_score: float | None = None
    for left_seat_id, right_seat_id in permutations(remaining_seat_ids, 2):
        score = score_partial_seat(
            student_id=left_student_id,
            seat_id=left_seat_id,
            mapping=mapping,
            context=context,
        )
        score += score_partial_seat(
            student_id=right_student_id,
            seat_id=right_seat_id,
            mapping={**mapping, left_student_id: left_seat_id},
            context=context,
        )
        if best_score is None or score > best_score + QUALITY_EPSILON:
            best_pair = (left_seat_id, right_seat_id)
            best_score = score
    if best_pair is None:
        raise ValueError(f"Expected at least one seat pair for {label} assignment.")
    return best_pair
