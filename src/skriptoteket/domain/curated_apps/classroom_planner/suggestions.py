"""Suggestion and randomization rules for classroom planner workspaces.

This module contains pure rule/scoring helpers for building explainable group
and seating proposals from a hydrated planner workspace. It also exposes a
separate randomizer used by the dedicated "Slumpa" flow in the UI.
"""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import datetime
from hashlib import sha256

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    ClassroomPlannerWorkspace,
    DraftGroup,
    GroupAssignment,
    PairConstraint,
    PairConstraintKind,
    PlanningProfile,
    PlanningProfileKind,
    SeatAssignment,
    Student,
    StudentPlanningMeta,
    SuggestionEngineMetadata,
    SuggestionList,
    SuggestionPlan,
)
from skriptoteket.domain.curated_apps.classroom_planner.validation import validate_workspace


def build_profile_suggestions(
    *,
    workspace: ClassroomPlannerWorkspace,
    generated_at: datetime,
) -> SuggestionList:
    """Build the default profile-based suggestions for a workspace."""

    suggestions = [
        _build_suggestion(
            workspace=workspace,
            generated_at=generated_at,
            profile_kind=PlanningProfileKind.FOCUS_FIRST,
            label="Fokus först",
        ),
        _build_suggestion(
            workspace=workspace,
            generated_at=generated_at,
            profile_kind=PlanningProfileKind.BALANCE_FIRST,
            label="Balans först",
        ),
        _build_suggestion(
            workspace=workspace,
            generated_at=generated_at,
            profile_kind=PlanningProfileKind.ROTATION_FIRST,
            label="Rotation först",
        ),
    ]
    return SuggestionList(suggestions=suggestions)


def build_randomized_suggestion(
    *,
    workspace: ClassroomPlannerWorkspace,
    generated_at: datetime,
    rng: random.Random,
) -> SuggestionPlan:
    """Build a fully randomized assignment proposal for the Slumpa flow."""

    groups = list(workspace.groups)
    students = list(workspace.roster.students)
    seats = list(workspace.template.seats)
    rng.shuffle(students)
    rng.shuffle(seats)

    group_assignments: list[GroupAssignment] = []
    for index, student in enumerate(students):
        group = groups[index % len(groups)]
        group_assignments.append(GroupAssignment(student_id=student.id, group_id=group.id))

    seat_assignments = [
        SeatAssignment(student_id=student.id, seat_id=seat.id)
        for student, seat in zip(students, seats, strict=False)
    ]

    suggestion = SuggestionPlan(
        suggestion_id="randomize",
        label="Slumpa",
        profile_kind=workspace.planning_profile.profile_kind,
        groups=groups,
        group_assignments=group_assignments,
        seat_assignments=seat_assignments,
        score_breakdown={"randomness": 1.0},
        findings=[],
        explanation_bullets=[
            "Alla elever fördelades slumpmässigt över grupper och platser.",
            "Planeringsregler användes inte som styrning i den här slumpningen.",
        ],
        engine_metadata=SuggestionEngineMetadata(
            suggestion_id="randomize",
            profile_kind=workspace.planning_profile.profile_kind,
            generated_at=generated_at,
            score_breakdown={"randomness": 1.0},
            explanation_bullets=[
                "Slumpa använder en dedikerad randomizer i stället för profilscoring.",
            ],
        ),
    )
    return _with_validation(workspace=workspace, suggestion=suggestion)


def build_suggestion_by_id(
    *,
    workspace: ClassroomPlannerWorkspace,
    suggestion_id: str,
    generated_at: datetime,
) -> SuggestionPlan:
    """Rebuild a deterministic profile suggestion from its stable id."""

    suggestion_map = {
        "focus-first": (PlanningProfileKind.FOCUS_FIRST, "Fokus först"),
        "balance-first": (PlanningProfileKind.BALANCE_FIRST, "Balans först"),
        "rotation-first": (PlanningProfileKind.ROTATION_FIRST, "Rotation först"),
    }
    if suggestion_id not in suggestion_map:
        raise KeyError(suggestion_id)
    profile_kind, label = suggestion_map[suggestion_id]
    return _build_suggestion(
        workspace=workspace,
        generated_at=generated_at,
        profile_kind=profile_kind,
        label=label,
    )


def _build_suggestion(
    *,
    workspace: ClassroomPlannerWorkspace,
    generated_at: datetime,
    profile_kind: PlanningProfileKind,
    label: str,
) -> SuggestionPlan:
    profile = workspace.planning_profile.model_copy(update={"profile_kind": profile_kind})
    groups = list(workspace.groups)
    students = _ordered_students(workspace=workspace, profile=profile)
    group_assignments = _assign_groups(
        students=students,
        groups=groups,
        current_group_by_student={
            assignment.student_id: assignment.group_id for assignment in workspace.group_assignments
        },
        constraints=workspace.pair_constraints if profile.enable_pair_constraints else [],
        profile=profile,
    )
    seat_assignments = _assign_seats(
        workspace=workspace,
        students=students,
        group_assignments=group_assignments,
        profile=profile,
    )
    score_breakdown = _score_workspace(
        workspace=workspace,
        group_assignments=group_assignments,
        seat_assignments=seat_assignments,
        profile=profile,
    )
    explanation_bullets = _explanations_for_profile(profile=profile)
    suggestion = SuggestionPlan(
        suggestion_id=profile_kind.value.replace("_", "-"),
        label=label,
        profile_kind=profile_kind,
        groups=groups,
        group_assignments=group_assignments,
        seat_assignments=seat_assignments,
        score_breakdown=score_breakdown,
        findings=[],
        explanation_bullets=explanation_bullets,
        engine_metadata=SuggestionEngineMetadata(
            suggestion_id=profile_kind.value.replace("_", "-"),
            profile_kind=profile_kind,
            generated_at=generated_at,
            score_breakdown=score_breakdown,
            explanation_bullets=explanation_bullets,
        ),
    )
    return _with_validation(workspace=workspace, suggestion=suggestion)


def _with_validation(
    *,
    workspace: ClassroomPlannerWorkspace,
    suggestion: SuggestionPlan,
) -> SuggestionPlan:
    proposed_workspace = workspace.model_copy(
        update={
            "groups": suggestion.groups,
            "group_assignments": suggestion.group_assignments,
            "seat_assignments": suggestion.seat_assignments,
        }
    )
    validation = validate_workspace(workspace=proposed_workspace)
    return suggestion.model_copy(update={"findings": validation.findings})


def _ordered_students(
    *,
    workspace: ClassroomPlannerWorkspace,
    profile: PlanningProfile,
) -> list[Student]:
    current_group_by_student = {
        assignment.student_id: assignment.group_id for assignment in workspace.group_assignments
    }
    meta_by_student = {meta.student_id: meta for meta in workspace.student_planning_meta}

    def score(student: Student) -> tuple[float, str]:
        meta = meta_by_student.get(student.id, StudentPlanningMeta(student_id=student.id))
        focus_score = (
            meta.teacher_proximity * profile.teacher_proximity_weight
            + meta.independent_focus_support * profile.focus_support_weight
            + meta.stability_preference * profile.stability_weight
        )
        if profile.profile_kind == PlanningProfileKind.FOCUS_FIRST:
            return (-focus_score, student.display_name)
        if profile.profile_kind == PlanningProfileKind.BALANCE_FIRST:
            current_group = current_group_by_student.get(student.id, "")
            return (len(current_group), student.display_name)
        digest = sha256(student.id.encode("utf-8"), usedforsecurity=False).hexdigest()
        rotation_penalty = 1 if current_group_by_student.get(student.id) else 0
        return (rotation_penalty, digest)

    return sorted(workspace.roster.students, key=score)


def _assign_groups(
    *,
    students: list[Student],
    groups: list[DraftGroup],
    current_group_by_student: dict[str, str],
    constraints: list[PairConstraint],
    profile: PlanningProfile,
) -> list[GroupAssignment]:
    members_by_group: dict[str, set[str]] = {group.id: set() for group in groups}
    constraint_map: dict[str, list[PairConstraint]] = defaultdict(list)
    for constraint in constraints:
        constraint_map[constraint.student_id_a].append(constraint)
        constraint_map[constraint.student_id_b].append(constraint)

    assignments: list[GroupAssignment] = []
    for student in students:
        best_group_id = groups[0].id
        best_score = float("-inf")
        for group in groups:
            score = 0.0
            score -= len(members_by_group[group.id]) * max(profile.balance_weight, 1)
            if profile.profile_kind == PlanningProfileKind.ROTATION_FIRST:
                if current_group_by_student.get(student.id) != group.id:
                    score += profile.rotation_weight * 2
            for constraint in constraint_map.get(student.id, []):
                peer_id = (
                    constraint.student_id_b
                    if constraint.student_id_a == student.id
                    else constraint.student_id_a
                )
                peer_in_group = peer_id in members_by_group[group.id]
                if constraint.kind in {
                    PairConstraintKind.KEEP_APART,
                    PairConstraintKind.TEMPORARY_CONFLICT,
                }:
                    score -= 100 if peer_in_group else 2
                if constraint.kind in {
                    PairConstraintKind.PREFER_TOGETHER,
                    PairConstraintKind.STABLE_PAIR,
                }:
                    score += 10 if peer_in_group else 0
            if score > best_score:
                best_score = score
                best_group_id = group.id
        members_by_group[best_group_id].add(student.id)
        assignments.append(GroupAssignment(student_id=student.id, group_id=best_group_id))
    return assignments


def _assign_seats(
    *,
    workspace: ClassroomPlannerWorkspace,
    students: list[Student],
    group_assignments: list[GroupAssignment],
    profile: PlanningProfile,
) -> list[SeatAssignment]:
    group_by_student = {
        assignment.student_id: assignment.group_id for assignment in group_assignments
    }
    meta_by_student = {meta.student_id: meta for meta in workspace.student_planning_meta}
    current_seat_by_student = {
        assignment.student_id: assignment.seat_id for assignment in workspace.seat_assignments
    }
    seats = list(workspace.template.seats)
    available_seats = set(seat.id for seat in seats)
    seat_by_id = {seat.id: seat for seat in seats}
    seat_assignments: list[SeatAssignment] = []
    assigned_seat_by_student: dict[str, str] = {}
    assigned_student_by_seat: dict[str, str] = {}

    for student in students:
        meta = meta_by_student.get(student.id, StudentPlanningMeta(student_id=student.id))
        best_seat_id = None
        best_score = float("-inf")
        for seat in seats:
            if seat.id not in available_seats:
                continue
            score = 0.0
            if profile.enable_zone_preferences:
                if meta.preferred_zone and seat.zone == meta.preferred_zone:
                    score += 10
                if meta.avoid_zone and seat.zone == meta.avoid_zone:
                    score -= 100
            score += max(0, 10 - seat.y) * meta.teacher_proximity * profile.teacher_proximity_weight
            if (
                current_seat_by_student.get(student.id) == seat.id
                and profile.profile_kind != PlanningProfileKind.ROTATION_FIRST
            ):
                score += meta.stability_preference * profile.stability_weight
            if (
                current_seat_by_student.get(student.id) == seat.id
                and profile.profile_kind == PlanningProfileKind.ROTATION_FIRST
            ):
                score -= 20
            for peer_assignment in seat_assignments:
                peer_group = group_by_student.get(peer_assignment.student_id)
                student_group = group_by_student.get(student.id)
                if peer_group and student_group and peer_group == student_group:
                    peer_seat = seat_by_id[peer_assignment.seat_id]
                    distance = abs(peer_seat.x - seat.x) + abs(peer_seat.y - seat.y)
                    if distance <= 120:
                        score += 3
            if score > best_score:
                best_score = score
                best_seat_id = seat.id
        if best_seat_id is None:
            continue
        available_seats.remove(best_seat_id)
        assigned_seat_by_student[student.id] = best_seat_id
        assigned_student_by_seat[best_seat_id] = student.id
        seat_assignments.append(SeatAssignment(student_id=student.id, seat_id=best_seat_id))
    return seat_assignments


def _score_workspace(
    *,
    workspace: ClassroomPlannerWorkspace,
    group_assignments: list[GroupAssignment],
    seat_assignments: list[SeatAssignment],
    profile: PlanningProfile,
) -> dict[str, float]:
    meta_by_student = {meta.student_id: meta for meta in workspace.student_planning_meta}
    seat_by_id = {seat.id: seat for seat in workspace.template.seats}
    group_sizes: dict[str, int] = defaultdict(int)
    for group_assignment in group_assignments:
        group_sizes[group_assignment.group_id] += 1
    balance_score = 0.0
    if group_sizes:
        sizes = list(group_sizes.values())
        balance_score = float(max(sizes) - min(sizes))
    teacher_score = 0.0
    zone_score = 0.0
    for seat_assignment in seat_assignments:
        meta = meta_by_student.get(seat_assignment.student_id)
        seat = seat_by_id[seat_assignment.seat_id]
        if meta is None:
            continue
        teacher_score += max(0, 10 - seat.y) * meta.teacher_proximity
        if meta.preferred_zone and seat.zone == meta.preferred_zone:
            zone_score += 1
    rotation_bonus = 0.0
    if profile.profile_kind == PlanningProfileKind.ROTATION_FIRST:
        current_group_by_student = {
            assignment.student_id: assignment.group_id for assignment in workspace.group_assignments
        }
        current_seat_by_student = {
            assignment.student_id: assignment.seat_id for assignment in workspace.seat_assignments
        }
        for group_assignment in group_assignments:
            if (
                current_group_by_student.get(group_assignment.student_id)
                != group_assignment.group_id
            ):
                rotation_bonus += 1
        for seat_assignment in seat_assignments:
            if current_seat_by_student.get(seat_assignment.student_id) != seat_assignment.seat_id:
                rotation_bonus += 1
    return {
        "balance": round(max(0.0, 10.0 - balance_score), 2),
        "teacher_proximity": round(teacher_score, 2),
        "zone_match": round(zone_score, 2),
        "rotation": round(rotation_bonus, 2),
    }


def _explanations_for_profile(*, profile: PlanningProfile) -> list[str]:
    bullets = {
        PlanningProfileKind.FOCUS_FIRST: [
            "Placering prioriterar elever med behov av lärarnärhet och fokusstöd.",
            "Stabilitet vägs högre än rotation i den här profilen.",
        ],
        PlanningProfileKind.BALANCE_FIRST: [
            "Fördelningen försöker jämna ut gruppstorlekar och undvika kluster.",
            "Profilen passar när läraren vill ha en neutral startpunkt att justera från.",
        ],
        PlanningProfileKind.ROTATION_FIRST: [
            "Förslaget försöker skapa variation jämfört med nuvarande utkast.",
            (
                "Rotation kan kombineras med senare historikregler "
                "när de aktiveras i en kommande slice."
            ),
        ],
    }[profile.profile_kind]
    if not profile.enable_pair_constraints:
        bullets.append("Parregler är avstängda och påverkar inte förslaget.")
    if not profile.enable_zone_preferences:
        bullets.append("Zonpreferenser är avstängda och påverkar inte platsvalet.")
    if profile.enable_history_rules:
        bullets.append(
            "Historikregler är påslagna i profilen men fungerar "
            "som förberedande no-op tills senare slice."
        )
    return bullets
