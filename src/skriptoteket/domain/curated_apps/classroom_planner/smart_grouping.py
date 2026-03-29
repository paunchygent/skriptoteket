"""Pure smart-grouping rules and search for Klassrumskartan.

Purpose:
    Own the backend-only grouping heuristics for the first smart-grouping
    slice.

Relationships:
    - consumed by the smart-grouping application handler
    - reuses the same visible relationship-rule model as smart seating while
      keeping grouping history and live seating continuity separate
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    GroupAssignment,
    RelationshipKind,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_scoring import (
    history_coassignment_counts,
    live_seating_pair_weights,
    normalized_partition_signature,
    normalized_size_deviation,
)

EXACT_ASSIGNMENT_LIMIT = 8
KEEP_NEAR_PAIR_REWARD = 8.0
KEEP_NEAR_PAIR_SPLIT_PENALTY = 8.0
KEEP_APART_PAIR_REWARD = 2.0
KEEP_APART_PAIR_COLLISION_PENALTY = 10.0
LIVE_SEATING_PAIR_REWARD = 4.0
GROUPING_HISTORY_PAIR_REPEAT_PENALTY = 5.0
SIZE_DEVIATION_PENALTY = 1.5


@dataclass(frozen=True)
class LiveSeatingContinuityInput:
    """Represent one current seating arrangement used for grouping continuity."""

    seats: list[Seat]
    seat_assignments: list[SeatAssignment]


@dataclass(frozen=True)
class SmartGroupingResult:
    """Return one scored smart-grouping candidate."""

    group_assignments: list[GroupAssignment]
    has_tradeoffs: bool


@dataclass(frozen=True)
class _CandidateScore:
    """Keep grouping precedence lexicographic across rule lanes."""

    explicit_rules: float
    live_seating: float
    history: float
    size_balance: float
    diversity: float
    has_tradeoffs: bool

    @property
    def ordering_key(self) -> tuple[float, float, float, float, float]:
        """Return the solver comparison tuple in priority order."""

        return (
            self.explicit_rules,
            self.live_seating,
            self.history,
            self.size_balance,
            self.diversity,
        )


def solve_smart_grouping(
    *,
    roster: Roster,
    groups: list[DraftGroup],
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> SmartGroupingResult:
    """Choose one best-effort grouping assignment for the current draft."""

    students = list(roster.students)
    ordered_groups = sorted(groups, key=lambda group: group.sort_order)
    if not students or not ordered_groups:
        return SmartGroupingResult(group_assignments=[], has_tradeoffs=False)

    if len(students) <= EXACT_ASSIGNMENT_LIMIT:
        best_mapping, best_score = _solve_exact(
            student_ids=tuple(student.id for student in students),
            group_ids=tuple(group.id for group in ordered_groups),
            smart_rules=smart_rules,
            current_group_assignments=current_group_assignments,
            history_checkpoints=history_checkpoints,
            live_seating_continuity=live_seating_continuity,
        )
    else:
        best_mapping, best_score = _solve_greedy(
            student_ids=tuple(student.id for student in students),
            group_ids=tuple(group.id for group in ordered_groups),
            smart_rules=smart_rules,
            current_group_assignments=current_group_assignments,
            history_checkpoints=history_checkpoints,
            live_seating_continuity=live_seating_continuity,
        )

    return SmartGroupingResult(
        group_assignments=[
            GroupAssignment(student_id=student_id, group_id=group_id)
            for student_id, group_id in sorted(best_mapping.items(), key=lambda item: item[0])
        ],
        has_tradeoffs=best_score.has_tradeoffs,
    )


def _solve_exact(
    *,
    student_ids: tuple[str, ...],
    group_ids: tuple[str, ...],
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> tuple[dict[str, str], _CandidateScore]:
    best_mapping: dict[str, str] | None = None
    best_score: _CandidateScore | None = None
    for candidate in product(group_ids, repeat=len(student_ids)):
        mapping = dict(zip(student_ids, candidate, strict=True))
        score = _score_candidate(
            assignments_by_student=mapping,
            group_ids=group_ids,
            smart_rules=smart_rules,
            current_group_assignments=current_group_assignments,
            history_checkpoints=history_checkpoints,
            live_seating_continuity=live_seating_continuity,
        )
        if best_score is None or score.ordering_key > best_score.ordering_key:
            best_mapping = mapping
            best_score = score
    assert best_mapping is not None
    assert best_score is not None
    return best_mapping, best_score


def _solve_greedy(
    *,
    student_ids: tuple[str, ...],
    group_ids: tuple[str, ...],
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> tuple[dict[str, str], _CandidateScore]:
    current_mapping: dict[str, str] = {}
    for student_id in student_ids:
        best_group_id = group_ids[0]
        best_score: _CandidateScore | None = None
        for group_id in group_ids:
            candidate_mapping = {**current_mapping, student_id: group_id}
            score = _score_candidate(
                assignments_by_student=candidate_mapping,
                group_ids=group_ids,
                smart_rules=smart_rules,
                current_group_assignments=current_group_assignments,
                history_checkpoints=history_checkpoints,
                live_seating_continuity=live_seating_continuity,
            )
            if best_score is None or score.ordering_key > best_score.ordering_key:
                best_group_id = group_id
                best_score = score
        current_mapping[student_id] = best_group_id
    final_score = _score_candidate(
        assignments_by_student=current_mapping,
        group_ids=group_ids,
        smart_rules=smart_rules,
        current_group_assignments=current_group_assignments,
        history_checkpoints=history_checkpoints,
        live_seating_continuity=live_seating_continuity,
    )
    return current_mapping, final_score


def _score_candidate(
    *,
    assignments_by_student: dict[str, str],
    group_ids: tuple[str, ...],
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
) -> _CandidateScore:
    keep_near_clusters = [
        tuple(sorted(rule.student_ids))
        for rule in smart_rules.relationship_rules
        if rule.kind is RelationshipKind.KEEP_NEAR
    ]
    keep_apart_clusters = [
        tuple(sorted(rule.student_ids))
        for rule in smart_rules.relationship_rules
        if rule.kind is RelationshipKind.KEEP_APART
    ]
    history_repeat_counts = history_coassignment_counts(history_checkpoints)
    live_pair_affinity = (
        live_seating_pair_weights(
            seats=live_seating_continuity.seats,
            seat_assignments_by_student={
                assignment.student_id: assignment.seat_id
                for assignment in live_seating_continuity.seat_assignments
            },
        )
        if live_seating_continuity is not None
        else {}
    )

    explicit_rules = 0.0
    live_seating = 0.0
    history = 0.0
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

    for pair, weight in live_pair_affinity.items():
        left_id, right_id = tuple(pair)
        if left_id not in assignments_by_student or right_id not in assignments_by_student:
            continue
        if assignments_by_student[left_id] == assignments_by_student[right_id]:
            live_seating += LIVE_SEATING_PAIR_REWARD * weight

    for pair, repeat_count in history_repeat_counts.items():
        left_id, right_id = tuple(pair)
        if left_id not in assignments_by_student or right_id not in assignments_by_student:
            continue
        if assignments_by_student[left_id] == assignments_by_student[right_id]:
            history -= GROUPING_HISTORY_PAIR_REPEAT_PENALTY * repeat_count

    size_balance = -SIZE_DEVIATION_PENALTY * normalized_size_deviation(
        assignments_by_student=assignments_by_student,
        group_ids=group_ids,
    )

    current_mapping = {
        assignment.student_id: assignment.group_id for assignment in current_group_assignments
    }
    diversity = 0.0
    if current_mapping:
        diversity = (
            1.0
            if normalized_partition_signature(assignments_by_student)
            != normalized_partition_signature(current_mapping)
            else 0.0
        )

    return _CandidateScore(
        explicit_rules=explicit_rules,
        live_seating=live_seating,
        history=history,
        size_balance=size_balance,
        diversity=diversity,
        has_tradeoffs=explicit_tradeoff,
    )
