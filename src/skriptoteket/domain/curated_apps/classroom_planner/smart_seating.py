"""Pure smart-seating rules and search for Klassrumskartan.

Purpose:
    Select one best-effort classroom seating assignment from roster rules,
    fixed-seat seeds, room topology, and checkpoint history.

Relationships:
    - Runs inside the classroom-planner domain layer without HTTP or
      persistence dependencies.
    - Delegates candidate scoring to smart-seating scoring helpers so search
      strategy and result assembly stay local to the solver.
"""

from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingExportCheckpoint,
)
from skriptoteket.domain.curated_apps.classroom_planner.fixed_seating import (
    build_fixed_seat_mapping,
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
from skriptoteket.domain.curated_apps.classroom_planner.seat_support_context import (
    build_seat_support_context,
    desired_near_teacher_seat_ids,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    build_seat_topology,
    infer_teaching_anchor,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    SmartRuleDiagnostic,
    build_smart_rule_diagnostics,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    SeatScoreContext,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_history import (
    build_seating_history_diversity,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_pattern_scoring import (
    current_keep_apart_block_signatures,
    current_keep_near_block_signatures,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_scoring import (
    current_keep_near_modes,
    current_keep_near_pair_seat_ids,
    near_teacher_history_counts,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_search import (
    solve_assignment_search,
)


@dataclass(frozen=True)
class SmartSeatingResult:
    """Return one scored smart-seating candidate."""

    seat_assignments: list[SeatAssignment]
    unplaced_student_ids: list[str]
    has_tradeoffs: bool
    rule_diagnostics: tuple[SmartRuleDiagnostic, ...] = ()


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
    fixed_mapping = build_fixed_seat_mapping(
        roster=roster,
        template=template,
        smart_rules=smart_rules,
    )
    if not students or not seats:
        return SmartSeatingResult(
            seat_assignments=[],
            unplaced_student_ids=[],
            has_tradeoffs=False,
            rule_diagnostics=(),
        )

    fixed_seat_ids = set(fixed_mapping.values())
    remaining_seats = [seat for seat in seats if seat.id not in fixed_seat_ids]
    assignable_student_ids = _prioritize_students(
        roster=roster,
        smart_rules=smart_rules,
        history_checkpoints=history_checkpoints,
    )
    assignable_student_ids = [
        student_id for student_id in assignable_student_ids if student_id not in fixed_mapping
    ][: len(remaining_seats)]
    assigned_student_ids = set(assignable_student_ids)
    unplaced_student_ids = [
        student.id
        for student in roster.students
        if student.id not in fixed_mapping and student.id not in assigned_student_ids
    ]

    context = _build_score_context(
        seats=seats,
        template=template,
        smart_rules=smart_rules,
        current_seat_assignments=current_seat_assignments,
        history_checkpoints=history_checkpoints,
        fixed_assignments_by_student=fixed_mapping,
    )

    best_mapping, best_score = solve_assignment_search(
        student_ids=assignable_student_ids,
        seats=remaining_seats,
        context=context,
    )

    seat_assignments = [
        SeatAssignment(student_id=student_id, seat_id=seat_id)
        for student_id, seat_id in sorted(
            {**fixed_mapping, **best_mapping}.items(), key=lambda item: item[0]
        )
    ]
    rule_diagnostics = build_smart_rule_diagnostics(
        roster=roster,
        template=template,
        smart_rules=smart_rules,
        seat_assignments=seat_assignments,
    )
    return SmartSeatingResult(
        seat_assignments=seat_assignments,
        unplaced_student_ids=sorted(unplaced_student_ids),
        has_tradeoffs=(
            best_score.has_tradeoffs
            or bool(unplaced_student_ids)
            or any(diagnostic.status != "satisfied" for diagnostic in rule_diagnostics)
        ),
        rule_diagnostics=rule_diagnostics,
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
    fixed_assignments_by_student: dict[str, str],
) -> SeatScoreContext:
    anchor = infer_teaching_anchor(template=template)
    topology = build_seat_topology(
        seats=seats,
        anchor=anchor,
        fixtures=template.fixtures,
    )
    seat_support_context = build_seat_support_context(
        seats=seats,
        fixtures=template.fixtures,
        anchor=anchor,
    )
    near_teacher_student_ids = {
        preference.student_id
        for preference in smart_rules.seating_preferences
        if preference.near_teacher
    }
    near_teacher_pool_seat_ids = desired_near_teacher_seat_ids(
        topology=topology,
        support_context=seat_support_context,
    )
    keep_near_clusters = [
        set(rule.student_ids)
        for rule in smart_rules.relationship_rules
        if rule.kind is RelationshipKind.KEEP_NEAR
    ]
    keep_apart_clusters = [
        set(rule.student_ids)
        for rule in smart_rules.relationship_rules
        if rule.kind is RelationshipKind.KEEP_APART
    ]
    current_assignments_by_student = {
        assignment.student_id: assignment.seat_id for assignment in current_seat_assignments
    }
    return SeatScoreContext(
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
        seat_support_context=seat_support_context,
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
        history_diversity=build_seating_history_diversity(
            history_checkpoints=history_checkpoints,
            keep_near_clusters=keep_near_clusters,
            keep_apart_clusters=keep_apart_clusters,
            fixed_student_ids=set(fixed_assignments_by_student),
        ),
        history_fingerprint="|".join(
            checkpoint.assignment_hash for checkpoint in history_checkpoints
        ),
        history_diversity_weight=0.4 if current_assignments_by_student else 1.0,
        block_ids=tuple(sorted(set(topology.block_id_by_seat.values()))),
        current_keep_near_block_signature_by_pair=current_keep_near_block_signatures(
            keep_near_clusters=keep_near_clusters,
            current_assignments_by_student=current_assignments_by_student,
            topology=topology,
        ),
        current_keep_apart_block_signature_by_pair=current_keep_apart_block_signatures(
            keep_apart_clusters=keep_apart_clusters,
            current_assignments_by_student=current_assignments_by_student,
            topology=topology,
        ),
        keep_near_clusters=keep_near_clusters,
        keep_apart_clusters=keep_apart_clusters,
        current_assignments_by_student=current_assignments_by_student,
        fixed_assignments_by_student=fixed_assignments_by_student,
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
