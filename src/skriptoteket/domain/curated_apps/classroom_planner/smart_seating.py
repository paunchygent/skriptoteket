"""Pure smart-seating rules and search for Klassrumskartan.

This module owns the backend-only seating heuristics for the first smart
assignment slice. It combines teacher-edge inference, roster-global smart
rules, checkpoint-backed teacher-distance fairness, and rerun diversity
without leaking HTTP or persistence concerns into the domain layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from itertools import combinations, permutations
from random import Random

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RoomFixture,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    KeepNearRelationMode,
    SeatPairTopology,
    SeatTopology,
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_scoring import (
    current_keep_near_modes,
    current_keep_near_pair_seat_ids,
    keep_near_pair_score,
    near_teacher_history_counts,
    near_teacher_score,
)

QUALITY_EPSILON = 1e-6
EXACT_ASSIGNMENT_LIMIT = 7
RANDOM_ATTEMPTS = 96
CURRENT_SEAT_REPEAT_PENALTY = 3.0
LAYOUT_REPEAT_PENALTY = 2.5


@dataclass(frozen=True)
class SmartSeatingResult:
    """Return one scored smart-seating candidate."""

    seat_assignments: list[SeatAssignment]
    unplaced_student_ids: list[str]
    has_tradeoffs: bool


@dataclass(frozen=True)
class _SeatScoreContext:
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


@dataclass(frozen=True)
class _CandidateScore:
    """Keep primary quality separate from secondary diversity preference."""

    quality: float
    diversity: float
    has_tradeoffs: bool


def solve_smart_seating(
    *,
    roster: Roster,
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    current_seat_assignments: list[SeatAssignment],
    history_checkpoints: list[SeatingExportCheckpoint],
) -> SmartSeatingResult:
    """Choose one best-effort seating assignment for the current draft."""

    students = list(roster.students)
    seats = list(template.seats)
    if not students or not seats:
        return SmartSeatingResult(seat_assignments=[], unplaced_student_ids=[], has_tradeoffs=False)

    assignable_student_ids = _prioritize_students(
        roster=roster,
        smart_rules=smart_rules,
        history_checkpoints=history_checkpoints,
    )
    assignable_student_ids = assignable_student_ids[: len(seats)]
    unplaced_student_ids = [
        student.id for student in roster.students if student.id not in set(assignable_student_ids)
    ]

    context = _build_score_context(
        seats=seats,
        template=template,
        smart_rules=smart_rules,
        current_seat_assignments=current_seat_assignments,
        history_checkpoints=history_checkpoints,
    )

    if len(assignable_student_ids) <= EXACT_ASSIGNMENT_LIMIT:
        best_mapping, best_score = _solve_exact(
            student_ids=assignable_student_ids,
            seats=seats,
            context=context,
        )
    else:
        best_mapping, best_score = _solve_greedy(
            student_ids=assignable_student_ids,
            seats=seats,
            context=context,
        )

    seat_assignments = [
        SeatAssignment(student_id=student_id, seat_id=seat_id)
        for student_id, seat_id in sorted(best_mapping.items(), key=lambda item: item[0])
    ]
    return SmartSeatingResult(
        seat_assignments=seat_assignments,
        unplaced_student_ids=sorted(unplaced_student_ids),
        has_tradeoffs=best_score.has_tradeoffs or bool(unplaced_student_ids),
    )


def _prioritize_students(
    *,
    roster: Roster,
    smart_rules: RosterSmartRules,
    history_checkpoints: list[SeatingExportCheckpoint],
) -> list[str]:
    near_teacher = {preference.student_id for preference in smart_rules.seating_preferences}
    history_means = _history_mean_distance_by_student(history_checkpoints)
    cluster_members = {
        student_id for rule in smart_rules.relationship_rules for student_id in rule.student_ids
    }
    return [
        student.id
        for student in sorted(
            roster.students,
            key=lambda student: (
                1 if student.id in near_teacher else 0,
                1 if student.id in cluster_members else 0,
                history_means.get(student.id, 0.5),
                student.display_name,
            ),
            reverse=True,
        )
    ]


def _build_score_context(
    *,
    seats: list[Seat],
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    current_seat_assignments: list[SeatAssignment],
    history_checkpoints: list[SeatingExportCheckpoint],
) -> _SeatScoreContext:
    topology = build_seat_topology(
        seats=seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )
    near_teacher_student_ids = {
        preference.student_id
        for preference in smart_rules.seating_preferences
        if preference.near_teacher
    }
    near_teacher_pool_seat_ids = topology.near_teacher_pool(
        seat_count=min(len(seats), len(near_teacher_student_ids) + 1),
    )
    keep_near_clusters = [
        set(rule.student_ids)
        for rule in smart_rules.relationship_rules
        if rule.kind is RelationshipKind.KEEP_NEAR
    ]
    current_assignments_by_student = {
        assignment.student_id: assignment.seat_id for assignment in current_seat_assignments
    }
    return _SeatScoreContext(
        topology=topology,
        near_teacher_student_ids=near_teacher_student_ids,
        near_teacher_student_count=len(near_teacher_student_ids),
        near_teacher_pool_rank_by_seat={
            seat_id: index for index, seat_id in enumerate(near_teacher_pool_seat_ids)
        },
        near_teacher_history_counts_by_student=near_teacher_history_counts(
            history_checkpoints=history_checkpoints,
            pool_seat_ids=set(near_teacher_pool_seat_ids),
        ),
        current_near_teacher_pool_seat_ids={
            current_assignments_by_student[student_id]
            for student_id in near_teacher_student_ids
            if student_id in current_assignments_by_student
            and current_assignments_by_student[student_id] in set(near_teacher_pool_seat_ids)
        },
        current_keep_near_mode_by_pair=current_keep_near_modes(
            keep_near_clusters=keep_near_clusters,
            current_assignments_by_student=current_assignments_by_student,
            topology=topology,
        ),
        current_keep_near_seat_ids_by_pair=current_keep_near_pair_seat_ids(
            keep_near_clusters=keep_near_clusters,
            current_assignments_by_student=current_assignments_by_student,
        ),
        history_targets_by_student={
            student_id: _rebalance_target_distance(mean_distance)
            for student_id, mean_distance in _history_mean_distance_by_student(
                history_checkpoints
            ).items()
        },
        keep_near_clusters=keep_near_clusters,
        keep_apart_clusters=[
            set(rule.student_ids)
            for rule in smart_rules.relationship_rules
            if rule.kind is RelationshipKind.KEEP_APART
        ],
        current_assignments_by_student=current_assignments_by_student,
    )


def _history_mean_distance_by_student(
    history_checkpoints: list[SeatingExportCheckpoint],
) -> dict[str, float]:
    distance_samples: dict[str, list[float]] = {}
    for checkpoint in history_checkpoints:
        anchor = infer_teaching_anchor(room_context=checkpoint.room_context)
        checkpoint_seats = [
            Seat.model_validate(seat.model_dump()) for seat in checkpoint.room_context.seats
        ]
        topology = build_seat_topology(
            seats=checkpoint_seats,
            anchor=anchor,
            fixtures=[
                RoomFixture.model_validate(fixture.model_dump())
                for fixture in checkpoint.room_context.fixtures
            ],
        )
        for placement in checkpoint.seating_snapshot.placed_assignments:
            if placement.seat_id not in topology.seats_by_id:
                continue
            normalized_distance = topology.normalized_teacher_distance(placement.seat_id)
            distance_samples.setdefault(placement.student_id, []).append(normalized_distance)
    return {
        student_id: sum(samples) / len(samples)
        for student_id, samples in distance_samples.items()
        if samples
    }


def _rebalance_target_distance(mean_distance: float) -> float:
    return max(0.0, min(1.0, 1.0 - mean_distance))


def _solve_exact(
    *,
    student_ids: list[str],
    seats: list[Seat],
    context: _SeatScoreContext,
) -> tuple[dict[str, str], _CandidateScore]:
    seat_ids = [seat.id for seat in seats]
    best_mapping: dict[str, str] | None = None
    best_score: _CandidateScore | None = None
    for candidate_seat_ids in permutations(seat_ids, len(student_ids)):
        mapping = dict(zip(student_ids, candidate_seat_ids, strict=True))
        score = _score_candidate(mapping=mapping, context=context)
        if _is_better_score(score=score, current_best=best_score):
            best_mapping = mapping
            best_score = score
    if best_mapping is None or best_score is None:
        return {}, _CandidateScore(quality=0.0, diversity=0.0, has_tradeoffs=False)
    return best_mapping, best_score


def _solve_greedy(
    *,
    student_ids: list[str],
    seats: list[Seat],
    context: _SeatScoreContext,
) -> tuple[dict[str, str], _CandidateScore]:
    seat_ids = [seat.id for seat in seats]
    seed_material = "|".join(
        [
            *sorted(student_ids),
            *sorted(
                f"{student}:{seat}"
                for student, seat in context.current_assignments_by_student.items()
            ),
        ]
    ).encode("utf-8")
    rng = Random(int.from_bytes(blake2b(seed_material, digest_size=8).digest(), "big"))
    best_mapping: dict[str, str] | None = None
    best_score: _CandidateScore | None = None

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
            keep_near_pair = _unassigned_keep_near_pair(
                student_id=student_id,
                mapping=mapping,
                context=context,
            )
            if keep_near_pair is not None:
                left_student_id, right_student_id = keep_near_pair
                left_seat_id, right_seat_id = _best_keep_near_pair_assignment(
                    student_ids=keep_near_pair,
                    remaining_seat_ids=remaining,
                    mapping=mapping,
                    context=context,
                )
                mapping[left_student_id] = left_seat_id
                mapping[right_student_id] = right_seat_id
                remaining.remove(left_seat_id)
                remaining.remove(right_seat_id)
                handled_student_ids.update(keep_near_pair)
                continue
            best_seat_id = max(
                remaining,
                key=lambda seat_id: _partial_seat_score(
                    student_id=student_id,
                    seat_id=seat_id,
                    mapping=mapping,
                    context=context,
                ),
            )
            mapping[student_id] = best_seat_id
            remaining.remove(best_seat_id)
            handled_student_ids.add(student_id)
        score = _score_candidate(mapping=mapping, context=context)
        if _is_better_score(score=score, current_best=best_score):
            best_mapping = mapping
            best_score = score

    if best_mapping is None or best_score is None:
        return {}, _CandidateScore(quality=0.0, diversity=0.0, has_tradeoffs=False)
    return best_mapping, best_score


def _assignment_order(
    *,
    student_ids: list[str],
    context: _SeatScoreContext,
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


def _max_cluster_size(*, student_id: str, clusters: list[set[str]]) -> int:
    """Return the largest active rule cluster that includes the student."""

    return max((len(cluster) for cluster in clusters if student_id in cluster), default=0)


def _unassigned_keep_near_pair(
    *,
    student_id: str,
    mapping: dict[str, str],
    context: _SeatScoreContext,
) -> tuple[str, str] | None:
    """Return a two-student keep-near pair when both seats can be chosen jointly."""

    for cluster in context.keep_near_clusters:
        if student_id not in cluster or len(cluster) != 2:
            continue
        left_id, right_id = sorted(cluster)
        if left_id in mapping or right_id in mapping:
            return None
        return left_id, right_id
    return None


def _best_keep_near_pair_assignment(
    *,
    student_ids: tuple[str, str],
    remaining_seat_ids: list[str],
    mapping: dict[str, str],
    context: _SeatScoreContext,
) -> tuple[str, str]:
    """Choose the best ordered seat pair for one compact keep-near pair."""

    left_student_id, right_student_id = student_ids
    best_pair: tuple[str, str] | None = None
    best_score: float | None = None
    for left_seat_id, right_seat_id in permutations(remaining_seat_ids, 2):
        score = _partial_seat_score(
            student_id=left_student_id,
            seat_id=left_seat_id,
            mapping=mapping,
            context=context,
        )
        score += _partial_seat_score(
            student_id=right_student_id,
            seat_id=right_seat_id,
            mapping={**mapping, left_student_id: left_seat_id},
            context=context,
        )
        if best_score is None or score > best_score + QUALITY_EPSILON:
            best_pair = (left_seat_id, right_seat_id)
            best_score = score
    if best_pair is None:
        raise ValueError("Expected at least one seat pair for keep-near assignment.")
    return best_pair


def _partial_seat_score(
    *,
    student_id: str,
    seat_id: str,
    mapping: dict[str, str],
    context: _SeatScoreContext,
) -> float:
    seat_distance = context.topology.normalized_teacher_distance(seat_id)
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
            peer_seat_id = mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += keep_near_pair_score(
                pair=context.topology.pair(seat_id, peer_seat_id),
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
            peer_seat_id = mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += _keep_apart_pair_score(
                pair=context.topology.pair(seat_id, peer_seat_id),
            )
    if context.current_assignments_by_student.get(student_id) == seat_id:
        score -= CURRENT_SEAT_REPEAT_PENALTY
    return score


def _score_candidate(
    *,
    mapping: dict[str, str],
    context: _SeatScoreContext,
) -> _CandidateScore:
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
            pair_score = keep_near_pair_score(
                pair=pair,
                current_mode=context.current_keep_near_mode_by_pair.get(
                    frozenset((left_id, right_id))
                ),
                pair_key=frozenset((left_id, right_id)),
                pair_seat_ids=frozenset((left_seat_id, right_seat_id)),
                current_pair_seat_ids=context.current_keep_near_seat_ids_by_pair.get(
                    frozenset((left_id, right_id))
                ),
            )
            quality += pair_score
            if _keep_near_has_tradeoff(pair):
                has_tradeoffs = True

    for cluster in context.keep_apart_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                has_tradeoffs = True
                continue
            pair = context.topology.pair(left_seat_id, right_seat_id)
            pair_score = _keep_apart_pair_score(
                pair=pair,
            )
            quality += pair_score
            if _keep_apart_has_tradeoff(pair):
                has_tradeoffs = True

    return _CandidateScore(quality=quality, diversity=diversity, has_tradeoffs=has_tradeoffs)


def _teacher_priority_score(
    *,
    student_id: str,
    seat_id: str,
    seat_distance: float,
    context: _SeatScoreContext,
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


def _keep_apart_pair_score(*, pair: SeatPairTopology) -> float:
    if pair.orthogonally_adjacent:
        return -32.0
    spread_score = pair.front_gap * 4.0 + pair.lateral_gap * 4.0
    if not pair.same_block:
        return spread_score + 8.0
    if pair.diagonal_neighbor:
        return spread_score + 1.5
    if pair.same_row or pair.same_column:
        return spread_score - 2.5
    return spread_score - 1.0


def _keep_near_has_tradeoff(pair: SeatPairTopology) -> bool:
    return pair.keep_near_relation_mode is None


def _keep_apart_has_tradeoff(pair: SeatPairTopology) -> bool:
    if pair.orthogonally_adjacent:
        return True
    if not pair.same_block:
        return False
    return pair.front_gap + pair.lateral_gap < 2


def _is_better_score(*, score: _CandidateScore, current_best: _CandidateScore | None) -> bool:
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
