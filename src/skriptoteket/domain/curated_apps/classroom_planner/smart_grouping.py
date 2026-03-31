"""Pure smart-grouping rules and search for Klassrumskartan.

Purpose:
    Own the backend-only grouping orchestration for the first smart-grouping
    slice while delegating scoring and helper math to smaller support modules.

Relationships:
    - consumed by the smart-grouping application handler
    - reuses the same visible relationship-rule model as smart seating while
      keeping grouping history and classroom-aware compactness separate
    - re-exports the current private helper names used by focused tests
"""

from __future__ import annotations

from itertools import combinations, product

from skriptoteket.domain.curated_apps.classroom_planner.grouping_checkpoints import (
    GroupingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DraftGroup,
    GroupAssignment,
    Roster,
    RosterSmartRules,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_solver_support import (
    build_static_scoring_context as _build_static_scoring_context,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_solver_support import (
    greedy_student_orders as _greedy_student_orders,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_solver_support import (
    score_candidate as _score_candidate,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_grouping_types import (
    ClassroomCompactnessConfig,
    GreedySearchConfig,
    LiveSeatingContinuityInput,
    SmartGroupingResult,
    _CandidateScore,
    _StaticScoringContext,
)

EXACT_ASSIGNMENT_LIMIT = 8
DEFAULT_CLASSROOM_COMPACTNESS_CONFIG = ClassroomCompactnessConfig()
DEFAULT_GREEDY_SEARCH_CONFIG = GreedySearchConfig()


def solve_smart_grouping(
    *,
    roster: Roster,
    groups: list[DraftGroup],
    smart_rules: RosterSmartRules,
    current_group_assignments: list[GroupAssignment],
    history_checkpoints: list[GroupingExportCheckpoint],
    live_seating_continuity: LiveSeatingContinuityInput | None,
    classroom_compactness_config: ClassroomCompactnessConfig = DEFAULT_CLASSROOM_COMPACTNESS_CONFIG,
    greedy_search_config: GreedySearchConfig = DEFAULT_GREEDY_SEARCH_CONFIG,
) -> SmartGroupingResult:
    """Choose one best-effort grouping assignment for the current draft."""

    students = list(roster.students)
    ordered_groups = sorted(groups, key=lambda group: group.sort_order)
    if not students or not ordered_groups:
        return SmartGroupingResult(group_assignments=[], has_tradeoffs=False)

    static_context = _build_static_scoring_context(
        smart_rules=smart_rules,
        current_group_assignments=current_group_assignments,
        history_checkpoints=history_checkpoints,
        live_seating_continuity=live_seating_continuity,
    )
    student_ids = tuple(student.id for student in students)
    group_ids = tuple(group.id for group in ordered_groups)
    if len(students) <= EXACT_ASSIGNMENT_LIMIT:
        best_mapping, best_score = _solve_exact(
            student_ids=student_ids,
            group_ids=group_ids,
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
        )
    else:
        best_mapping, best_score = _solve_greedy(
            student_ids=student_ids,
            group_ids=group_ids,
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
            greedy_search_config=greedy_search_config,
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
    static_context: _StaticScoringContext,
    classroom_compactness_config: ClassroomCompactnessConfig,
) -> tuple[dict[str, str], _CandidateScore]:
    best_mapping: dict[str, str] | None = None
    best_score: _CandidateScore | None = None
    for candidate in product(group_ids, repeat=len(student_ids)):
        mapping = dict(zip(student_ids, candidate, strict=True))
        score = _score_candidate(
            assignments_by_student=mapping,
            group_ids=group_ids,
            total_student_count=len(student_ids),
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
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
    static_context: _StaticScoringContext,
    classroom_compactness_config: ClassroomCompactnessConfig,
    greedy_search_config: GreedySearchConfig,
) -> tuple[dict[str, str], _CandidateScore]:
    best_mapping: dict[str, str] | None = None
    best_score: _CandidateScore | None = None
    for ordered_student_ids in _greedy_student_orders(
        student_ids=student_ids,
        static_context=static_context,
        greedy_search_config=greedy_search_config,
    ):
        current_mapping: dict[str, str] = {}
        for student_id in ordered_student_ids:
            best_group_id = group_ids[0]
            candidate_best_score: _CandidateScore | None = None
            for group_id in group_ids:
                candidate_mapping = {**current_mapping, student_id: group_id}
                score = _score_candidate(
                    assignments_by_student=candidate_mapping,
                    group_ids=group_ids,
                    total_student_count=len(student_ids),
                    static_context=static_context,
                    classroom_compactness_config=classroom_compactness_config,
                )
                if (
                    candidate_best_score is None
                    or score.ordering_key > candidate_best_score.ordering_key
                ):
                    best_group_id = group_id
                    candidate_best_score = score
            current_mapping[student_id] = best_group_id
        final_score = _score_candidate(
            assignments_by_student=current_mapping,
            group_ids=group_ids,
            total_student_count=len(student_ids),
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
        )
        current_mapping, final_score = _improve_by_pair_swaps(
            assignments_by_student=current_mapping,
            current_score=final_score,
            group_ids=group_ids,
            total_student_count=len(student_ids),
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
        )
        if best_score is None or final_score.ordering_key > best_score.ordering_key:
            best_mapping = current_mapping
            best_score = final_score
    assert best_mapping is not None
    assert best_score is not None
    return best_mapping, best_score


def _improve_by_pair_swaps(
    *,
    assignments_by_student: dict[str, str],
    current_score: _CandidateScore,
    group_ids: tuple[str, ...],
    total_student_count: int,
    static_context: _StaticScoringContext,
    classroom_compactness_config: ClassroomCompactnessConfig,
) -> tuple[dict[str, str], _CandidateScore]:
    """Try one final improving cross-group swap after greedy construction."""

    best_swap_mapping: dict[str, str] | None = None
    best_swap_score: _CandidateScore | None = None
    for left_id, right_id in combinations(sorted(assignments_by_student), 2):
        if assignments_by_student[left_id] == assignments_by_student[right_id]:
            continue
        candidate_mapping = dict(assignments_by_student)
        candidate_mapping[left_id], candidate_mapping[right_id] = (
            candidate_mapping[right_id],
            candidate_mapping[left_id],
        )
        candidate_score = _score_candidate(
            assignments_by_student=candidate_mapping,
            group_ids=group_ids,
            total_student_count=total_student_count,
            static_context=static_context,
            classroom_compactness_config=classroom_compactness_config,
        )
        if candidate_score.ordering_key <= current_score.ordering_key:
            continue
        if best_swap_score is None or candidate_score.ordering_key > best_swap_score.ordering_key:
            best_swap_mapping = candidate_mapping
            best_swap_score = candidate_score
    if best_swap_mapping is None or best_swap_score is None:
        return dict(assignments_by_student), current_score
    return best_swap_mapping, best_swap_score
