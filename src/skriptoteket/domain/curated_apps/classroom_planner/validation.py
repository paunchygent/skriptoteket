"""Validation rules for classroom planner workspaces.

This module performs authoritative planner validation over the hydrated
workspace. It checks structural invariants first, then evaluates teacher-only
constraints and preference rules according to the active planning profile
toggles.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    PairConstraintKind,
    ValidationFinding,
    ValidationResult,
    ValidationSeverity,
    is_valid_lesson_mode_id,
)


def _make_finding(
    *,
    severity: ValidationSeverity,
    code: str,
    message: str,
    explanation: str,
    subject_ref: str | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        severity=severity,
        code=code,
        subject_ref=subject_ref,
        message=message,
        explanation=explanation,
    )


def validate_workspace(*, workspace: ClassroomPlannerWorkspace) -> ValidationResult:
    """Return normalized validation findings for a planner workspace."""

    findings: list[ValidationFinding] = []
    roster_student_ids = [student.id for student in workspace.roster.students]
    seat_ids = [seat.id for seat in workspace.template.seats]
    group_ids = [group.id for group in workspace.groups]
    group_sort_orders = [group.sort_order for group in workspace.groups]

    if not is_valid_lesson_mode_id(lesson_mode_id=workspace.draft.lesson_mode_id):
        findings.append(
            _make_finding(
                severity=ValidationSeverity.HARD,
                code="invalid_lesson_mode",
                subject_ref=workspace.draft.lesson_mode_id,
                message="Ogiltigt lektionsläge.",
                explanation=(
                    "Utkastet refererar till ett lektionsläge som inte finns i bootstrap-katalogen."
                ),
            )
        )

    for student_id, count in Counter(roster_student_ids).items():
        if count > 1:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_roster_student",
                    subject_ref=f"student:{student_id}",
                    message="Dubblett i klasslistan.",
                    explanation=(
                        "Varje elev-id måste vara unikt inom en klasslista "
                        "för att planeringen ska vara deterministisk."
                    ),
                )
            )

    for seat_id, count in Counter(seat_ids).items():
        if count > 1:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_template_seat",
                    subject_ref=f"seat:{seat_id}",
                    message="Dubblett i klassrummet.",
                    explanation="Varje plats-id måste vara unikt inom en rumsmall.",
                )
            )

    for group_id, count in Counter(group_ids).items():
        if count > 1:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_group_id",
                    subject_ref=f"group:{group_id}",
                    message="Dubblett bland grupper.",
                    explanation="Varje grupp-id måste vara stabilt och unikt inom ett utkast.",
                )
            )

    for sort_order, count in Counter(group_sort_orders).items():
        if count > 1:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_group_sort_order",
                    subject_ref=f"group-sort:{sort_order}",
                    message="Två grupper delar samma ordningstal.",
                    explanation=(
                        "Gruppordningen måste vara entydig för att "
                        "drag-och-släpp och export ska bli stabil."
                    ),
                )
            )

    roster_student_id_set = set(roster_student_ids)
    seat_id_set = set(seat_ids)
    group_id_set = set(group_ids)

    group_assignments_by_student: dict[str, str] = {}
    students_by_group: dict[str, set[str]] = defaultdict(set)
    for group_assignment in workspace.group_assignments:
        if group_assignment.student_id not in roster_student_id_set:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="unknown_group_assignment_student",
                    subject_ref=f"student:{group_assignment.student_id}",
                    message="Grupptilldelning refererar till okänd elev.",
                    explanation=(
                        "Alla gruppkopplingar måste peka på elever som finns i vald klasslista."
                    ),
                )
            )
        if group_assignment.group_id not in group_id_set:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="unknown_group_assignment_group",
                    subject_ref=f"group:{group_assignment.group_id}",
                    message="Grupptilldelning refererar till okänd grupp.",
                    explanation="Alla gruppkopplingar måste peka på en befintlig grupp i utkastet.",
                )
            )
        if group_assignment.student_id in group_assignments_by_student:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_group_assignment_student",
                    subject_ref=f"student:{group_assignment.student_id}",
                    message="Eleven finns i flera grupper.",
                    explanation="En elev får bara ha en grupptilldelning inom samma utkast.",
                )
            )
        group_assignments_by_student[group_assignment.student_id] = group_assignment.group_id
        students_by_group[group_assignment.group_id].add(group_assignment.student_id)

    seat_assignments_by_student: dict[str, str] = {}
    students_by_seat: dict[str, str] = {}
    for seat_assignment in workspace.seat_assignments:
        if seat_assignment.student_id not in roster_student_id_set:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="unknown_seat_assignment_student",
                    subject_ref=f"student:{seat_assignment.student_id}",
                    message="Platskoppling refererar till okänd elev.",
                    explanation=(
                        "Alla platskopplingar måste peka på elever som finns i vald klasslista."
                    ),
                )
            )
        if seat_assignment.seat_id not in seat_id_set:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="unknown_seat_assignment_seat",
                    subject_ref=f"seat:{seat_assignment.seat_id}",
                    message="Platskoppling refererar till okänd plats.",
                    explanation=(
                        "Alla platskopplingar måste peka på platser som finns i vald rumsmall."
                    ),
                )
            )
        if seat_assignment.student_id in seat_assignments_by_student:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_seat_assignment_student",
                    subject_ref=f"student:{seat_assignment.student_id}",
                    message="Eleven sitter på flera platser.",
                    explanation="En elev får bara ha en plats inom samma utkast.",
                )
            )
        if seat_assignment.seat_id in students_by_seat:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="duplicate_seat_assignment_seat",
                    subject_ref=f"seat:{seat_assignment.seat_id}",
                    message="Platsen används av flera elever.",
                    explanation="Varje plats kan bara vara upptagen av en elev åt gången.",
                )
            )
        seat_assignments_by_student[seat_assignment.student_id] = seat_assignment.seat_id
        students_by_seat[seat_assignment.seat_id] = seat_assignment.student_id

    student_meta_by_id = {meta.student_id: meta for meta in workspace.student_planning_meta}
    for student_id in student_meta_by_id:
        if student_id not in roster_student_id_set:
            findings.append(
                _make_finding(
                    severity=ValidationSeverity.HARD,
                    code="unknown_student_meta_student",
                    subject_ref=f"student:{student_id}",
                    message="Planeringsmetadata refererar till okänd elev.",
                    explanation=(
                        "Teacher-only metadata måste vara knuten till en elev i vald klasslista."
                    ),
                )
            )

    if workspace.planning_profile.enable_pair_constraints:
        for constraint in workspace.pair_constraints:
            if (
                constraint.student_id_a not in roster_student_id_set
                or constraint.student_id_b not in roster_student_id_set
            ):
                findings.append(
                    _make_finding(
                        severity=ValidationSeverity.HARD,
                        code="unknown_pair_constraint_student",
                        subject_ref=f"pair:{constraint.student_id_a}:{constraint.student_id_b}",
                        message="Parregel refererar till okänd elev.",
                        explanation="Alla parregler måste referera till elever i vald klasslista.",
                    )
                )
                continue
            if constraint.student_id_a == constraint.student_id_b:
                findings.append(
                    _make_finding(
                        severity=ValidationSeverity.HARD,
                        code="invalid_pair_constraint_self",
                        subject_ref=f"student:{constraint.student_id_a}",
                        message="En elev kan inte ha en parregel med sig själv.",
                        explanation="Parregler kräver två olika elev-id:n.",
                    )
                )
                continue

            group_a = group_assignments_by_student.get(constraint.student_id_a)
            group_b = group_assignments_by_student.get(constraint.student_id_b)
            if group_a and group_b:
                if (
                    constraint.kind
                    in {PairConstraintKind.KEEP_APART, PairConstraintKind.TEMPORARY_CONFLICT}
                    and group_a == group_b
                ):
                    findings.append(
                        _make_finding(
                            severity=ValidationSeverity.HARD,
                            code="pair_constraint_same_group",
                            subject_ref=f"pair:{constraint.student_id_a}:{constraint.student_id_b}",
                            message="Två elever som ska hållas isär ligger i samma grupp.",
                            explanation=(
                                "Den aktiva parregeln markerar att paret "
                                "inte får placeras i samma grupp."
                            ),
                        )
                    )
                if (
                    constraint.kind
                    in {PairConstraintKind.PREFER_TOGETHER, PairConstraintKind.STABLE_PAIR}
                    and group_a != group_b
                ):
                    findings.append(
                        _make_finding(
                            severity=ValidationSeverity.SOFT,
                            code="pair_constraint_split_group",
                            subject_ref=f"pair:{constraint.student_id_a}:{constraint.student_id_b}",
                            message="Ett önskat par ligger i olika grupper.",
                            explanation=(
                                "Den här parregeln är vägledande och kan "
                                "brytas, men bör motiveras i planeringen."
                            ),
                        )
                    )

    if workspace.planning_profile.enable_zone_preferences:
        seat_zone_by_id = {seat.id: seat.zone for seat in workspace.template.seats}
        for student_id, seat_id in seat_assignments_by_student.items():
            meta = student_meta_by_id.get(student_id)
            if meta is None:
                continue
            zone = seat_zone_by_id.get(seat_id)
            if meta.avoid_zone and zone == meta.avoid_zone:
                findings.append(
                    _make_finding(
                        severity=ValidationSeverity.HARD,
                        code="avoid_zone_violation",
                        subject_ref=f"student:{student_id}",
                        message="Eleven sitter i en undvik-zon.",
                        explanation=(
                            "Den valda platsen bryter mot den markerade zon som eleven bör undvika."
                        ),
                    )
                )
            if meta.preferred_zone and zone != meta.preferred_zone:
                findings.append(
                    _make_finding(
                        severity=ValidationSeverity.SOFT,
                        code="preferred_zone_unmet",
                        subject_ref=f"student:{student_id}",
                        message="Elevens önskade zon uppfylls inte.",
                        explanation=(
                            "Det här är en preferens, inte ett blockerande "
                            "fel, men bör vägas in i förslagen."
                        ),
                    )
                )

    if workspace.planning_profile.enable_history_rules:
        findings.append(
            _make_finding(
                severity=ValidationSeverity.SOFT,
                code="history_rules_reserved",
                message="Historikregler är förberedda men inte aktiva ännu.",
                explanation=(
                    "Växeln finns redan i modellen för framtida "
                    "slice-arbete, men tidigare placeringar påverkar "
                    "inte resultatet ännu."
                ),
            )
        )

    return ValidationResult(findings=findings)
