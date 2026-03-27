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
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RelationshipKind,
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Roster,
    RosterSmartRules,
    Seat,
    SeatAssignment,
)

QUALITY_EPSILON = 1e-6
EXACT_ASSIGNMENT_LIMIT = 7
RANDOM_ATTEMPTS = 48


@dataclass(frozen=True)
class TeachingAnchor:
    """Describe the inferred teaching/front edge for one room."""

    edge: str
    x: float
    y: float


@dataclass(frozen=True)
class SmartSeatingResult:
    """Return one scored smart-seating candidate."""

    seat_assignments: list[SeatAssignment]
    unplaced_student_ids: list[str]
    has_tradeoffs: bool


@dataclass(frozen=True)
class _Bounds:
    max_x: float
    max_y: float


@dataclass(frozen=True)
class _SeatScoreContext:
    anchor: TeachingAnchor
    normalized_teacher_distance_by_seat: dict[str, float]
    rank_positions_by_seat: dict[str, tuple[int, int]]
    near_teacher_student_ids: set[str]
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


def infer_teaching_anchor(
    *,
    template: RoomTemplate | None = None,
    room_context: SeatingRoomContextSnapshot | None = None,
) -> TeachingAnchor:
    """Infer the active teaching/front edge from room cues or a safe default."""

    if (template is None) == (room_context is None):
        raise ValueError("Provide exactly one of template or room_context.")
    seats, fixtures, bounds = _extract_room_parts(template=template, room_context=room_context)

    del seats
    whiteboards = [fixture for fixture in fixtures if fixture.type is RoomFixtureType.WHITEBOARD]
    if whiteboards:
        return _anchor_from_fixtures(fixtures=whiteboards, bounds=bounds, weight_to_center=0.0)

    teacher_desks = [
        fixture for fixture in fixtures if fixture.type is RoomFixtureType.TEACHER_DESK
    ]
    if teacher_desks:
        return _anchor_from_fixtures(fixtures=teacher_desks, bounds=bounds, weight_to_center=0.65)

    return TeachingAnchor(edge="top", x=bounds.max_x / 2, y=0.0)


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
        students=students,
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


def _extract_room_parts(
    *,
    template: RoomTemplate | None,
    room_context: SeatingRoomContextSnapshot | None,
) -> tuple[list[Seat], list[RoomFixture], _Bounds]:
    if template is not None:
        seats = list(template.seats)
        fixtures = list(template.fixtures)
        max_x = max(
            [float(template.grid_cols)]
            + [float(seat.x) for seat in template.seats]
            + [float(fixture.x + fixture.width) for fixture in template.fixtures]
        )
        max_y = max(
            [float(template.grid_rows)]
            + [float(seat.y) for seat in template.seats]
            + [float(fixture.y + fixture.height) for fixture in template.fixtures]
        )
        return seats, fixtures, _Bounds(max_x=max_x, max_y=max_y)

    if room_context is None:
        raise ValueError("Room context is required.")

    seats = [Seat.model_validate(seat.model_dump()) for seat in room_context.seats]
    fixtures = [
        RoomFixture.model_validate(fixture.model_dump()) for fixture in room_context.fixtures
    ]
    max_x = max(
        [float(room_context.grid_cols)]
        + [float(seat.x) for seat in room_context.seats]
        + [float(fixture.x + fixture.width) for fixture in room_context.fixtures]
    )
    max_y = max(
        [float(room_context.grid_rows)]
        + [float(seat.y) for seat in room_context.seats]
        + [float(fixture.y + fixture.height) for fixture in room_context.fixtures]
    )
    return seats, fixtures, _Bounds(max_x=max_x, max_y=max_y)


def _anchor_from_fixtures(
    *,
    fixtures: list[RoomFixture],
    bounds: _Bounds,
    weight_to_center: float,
) -> TeachingAnchor:
    wall = _best_wall(fixtures=fixtures, bounds=bounds)
    average_center_x = sum(_fixture_center(fixture)[0] for fixture in fixtures) / len(fixtures)
    average_center_y = sum(_fixture_center(fixture)[1] for fixture in fixtures) / len(fixtures)
    room_center_x = bounds.max_x / 2
    room_center_y = bounds.max_y / 2

    if wall == "top":
        anchor_x = _mix(room_center_x, average_center_x, 1 - weight_to_center)
        return TeachingAnchor(edge=wall, x=anchor_x, y=0.0)
    if wall == "bottom":
        anchor_x = _mix(room_center_x, average_center_x, 1 - weight_to_center)
        return TeachingAnchor(edge=wall, x=anchor_x, y=bounds.max_y)
    if wall == "left":
        anchor_y = _mix(room_center_y, average_center_y, 1 - weight_to_center)
        return TeachingAnchor(edge=wall, x=0.0, y=anchor_y)

    anchor_y = _mix(room_center_y, average_center_y, 1 - weight_to_center)
    return TeachingAnchor(edge=wall, x=bounds.max_x, y=anchor_y)


def _best_wall(*, fixtures: list[RoomFixture], bounds: _Bounds) -> str:
    scores = {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}
    for fixture in fixtures:
        wall_distances = {
            "top": float(fixture.y),
            "bottom": float(max(bounds.max_y - (fixture.y + fixture.height), 0.0)),
            "left": float(fixture.x),
            "right": float(max(bounds.max_x - (fixture.x + fixture.width), 0.0)),
        }
        nearest_distance = min(wall_distances.values())
        for wall, distance in wall_distances.items():
            if abs(distance - nearest_distance) <= QUALITY_EPSILON:
                scores[wall] += 1.0
            scores[wall] -= distance * 0.01
    return max(scores.items(), key=lambda item: (item[1], item[0]))[0]


def _fixture_center(fixture: RoomFixture) -> tuple[float, float]:
    return (fixture.x + fixture.width / 2, fixture.y + fixture.height / 2)


def _mix(center_value: float, cue_value: float, cue_weight: float) -> float:
    return center_value * (1 - cue_weight) + cue_value * cue_weight


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
    students: list,
    seats: list[Seat],
    template: RoomTemplate,
    smart_rules: RosterSmartRules,
    current_seat_assignments: list[SeatAssignment],
    history_checkpoints: list[SeatingExportCheckpoint],
) -> _SeatScoreContext:
    del students
    anchor = infer_teaching_anchor(template=template)
    rank_positions_by_seat = _seat_rank_positions(seats)
    normalized_teacher_distance_by_seat = _teacher_distances(
        seats=seats,
        anchor=anchor,
        rank_positions_by_seat=rank_positions_by_seat,
    )
    return _SeatScoreContext(
        anchor=anchor,
        normalized_teacher_distance_by_seat=normalized_teacher_distance_by_seat,
        rank_positions_by_seat=rank_positions_by_seat,
        near_teacher_student_ids={
            preference.student_id
            for preference in smart_rules.seating_preferences
            if preference.near_teacher
        },
        history_targets_by_student={
            student_id: _rebalance_target_distance(mean_distance)
            for student_id, mean_distance in _history_mean_distance_by_student(
                history_checkpoints
            ).items()
        },
        keep_near_clusters=[
            set(rule.student_ids)
            for rule in smart_rules.relationship_rules
            if rule.kind is RelationshipKind.KEEP_NEAR
        ],
        keep_apart_clusters=[
            set(rule.student_ids)
            for rule in smart_rules.relationship_rules
            if rule.kind is RelationshipKind.KEEP_APART
        ],
        current_assignments_by_student={
            assignment.student_id: assignment.seat_id for assignment in current_seat_assignments
        },
    )


def _history_mean_distance_by_student(
    history_checkpoints: list[SeatingExportCheckpoint],
) -> dict[str, float]:
    distance_samples: dict[str, list[float]] = {}
    for checkpoint in history_checkpoints:
        anchor = infer_teaching_anchor(room_context=checkpoint.room_context)
        rank_positions = _seat_rank_positions(
            [Seat.model_validate(seat.model_dump()) for seat in checkpoint.room_context.seats]
        )
        seat_lookup = {
            seat.id: Seat.model_validate(seat.model_dump())
            for seat in checkpoint.room_context.seats
        }
        distances = _teacher_distances(
            seats=list(seat_lookup.values()),
            anchor=anchor,
            rank_positions_by_seat=rank_positions,
        )
        for placement in checkpoint.seating_snapshot.placed_assignments:
            normalized_distance = distances.get(placement.seat_id)
            if normalized_distance is None:
                continue
            distance_samples.setdefault(placement.student_id, []).append(normalized_distance)
    return {
        student_id: sum(samples) / len(samples)
        for student_id, samples in distance_samples.items()
        if samples
    }


def _rebalance_target_distance(mean_distance: float) -> float:
    if mean_distance <= 0.5:
        return min(1.0, mean_distance + 0.4)
    return max(0.0, mean_distance - 0.4)


def _seat_rank_positions(seats: list[Seat]) -> dict[str, tuple[int, int]]:
    unique_x = {value: index for index, value in enumerate(sorted({seat.x for seat in seats}))}
    unique_y = {value: index for index, value in enumerate(sorted({seat.y for seat in seats}))}
    return {seat.id: (unique_x[seat.x], unique_y[seat.y]) for seat in seats}


def _teacher_distances(
    *,
    seats: list[Seat],
    anchor: TeachingAnchor,
    rank_positions_by_seat: dict[str, tuple[int, int]],
) -> dict[str, float]:
    raw_distances = {
        seat.id: ((seat.x - anchor.x) ** 2 + (seat.y - anchor.y) ** 2) ** 0.5 for seat in seats
    }
    room_scale = max(
        max(raw_distances.values(), default=0.0),
        len({position[0] for position in rank_positions_by_seat.values()}) - 1,
        len({position[1] for position in rank_positions_by_seat.values()}) - 1,
        1,
    )
    return {seat_id: raw_distance / room_scale for seat_id, raw_distance in raw_distances.items()}


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

    for _ in range(RANDOM_ATTEMPTS):
        remaining = seat_ids.copy()
        rng.shuffle(remaining)
        order = student_ids.copy()
        rng.shuffle(order)
        mapping: dict[str, str] = {}
        for student_id in order:
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
        score = _score_candidate(mapping=mapping, context=context)
        if _is_better_score(score=score, current_best=best_score):
            best_mapping = mapping
            best_score = score

    if best_mapping is None or best_score is None:
        return {}, _CandidateScore(quality=0.0, diversity=0.0, has_tradeoffs=False)
    return best_mapping, best_score


def _partial_seat_score(
    *,
    student_id: str,
    seat_id: str,
    mapping: dict[str, str],
    context: _SeatScoreContext,
) -> float:
    seat_distance = context.normalized_teacher_distance_by_seat[seat_id]
    score = _teacher_priority_score(
        student_id=student_id, seat_distance=seat_distance, context=context
    )
    for cluster in context.keep_near_clusters:
        if student_id not in cluster:
            continue
        for peer_id in cluster:
            peer_seat_id = mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += _keep_near_pair_score(
                seat_id=seat_id, peer_seat_id=peer_seat_id, context=context
            )
    for cluster in context.keep_apart_clusters:
        if student_id not in cluster:
            continue
        for peer_id in cluster:
            peer_seat_id = mapping.get(peer_id)
            if peer_id == student_id or peer_seat_id is None:
                continue
            score += _keep_apart_pair_score(
                seat_id=seat_id,
                peer_seat_id=peer_seat_id,
                context=context,
            )
    if context.current_assignments_by_student.get(student_id) == seat_id:
        score -= 0.2
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
        seat_distance = context.normalized_teacher_distance_by_seat[seat_id]
        quality += _teacher_priority_score(
            student_id=student_id, seat_distance=seat_distance, context=context
        )
        if context.current_assignments_by_student.get(student_id) == seat_id:
            diversity -= 1.0

    for cluster in context.keep_near_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                has_tradeoffs = True
                continue
            pair_score = _keep_near_pair_score(
                seat_id=left_seat_id,
                peer_seat_id=right_seat_id,
                context=context,
            )
            quality += pair_score
            if _rank_distance(left_seat_id, right_seat_id, context=context) > 2:
                has_tradeoffs = True

    for cluster in context.keep_apart_clusters:
        for left_id, right_id in combinations(sorted(cluster), 2):
            left_seat_id = mapping.get(left_id)
            right_seat_id = mapping.get(right_id)
            if left_seat_id is None or right_seat_id is None:
                has_tradeoffs = True
                continue
            pair_score = _keep_apart_pair_score(
                seat_id=left_seat_id,
                peer_seat_id=right_seat_id,
                context=context,
            )
            quality += pair_score
            if _orthogonally_adjacent(left_seat_id, right_seat_id, context=context):
                has_tradeoffs = True

    return _CandidateScore(quality=quality, diversity=diversity, has_tradeoffs=has_tradeoffs)


def _teacher_priority_score(
    *,
    student_id: str,
    seat_distance: float,
    context: _SeatScoreContext,
) -> float:
    if student_id in context.near_teacher_student_ids:
        return (1.0 - seat_distance) * 8.0
    target_distance = context.history_targets_by_student.get(student_id)
    if target_distance is None:
        return (1.0 - abs(seat_distance - 0.5)) * 0.4
    return (1.0 - abs(seat_distance - target_distance)) * 6.0


def _keep_near_pair_score(
    *,
    seat_id: str,
    peer_seat_id: str,
    context: _SeatScoreContext,
) -> float:
    rank_distance = _rank_distance(seat_id, peer_seat_id, context=context)
    return max(0.0, 5.0 - rank_distance * 1.5)


def _keep_apart_pair_score(
    *,
    seat_id: str,
    peer_seat_id: str,
    context: _SeatScoreContext,
) -> float:
    rank_distance = _rank_distance(seat_id, peer_seat_id, context=context)
    if _orthogonally_adjacent(seat_id, peer_seat_id, context=context):
        return -12.0
    return min(rank_distance, 5) * 1.8


def _rank_distance(
    seat_id: str,
    peer_seat_id: str,
    *,
    context: _SeatScoreContext,
) -> int:
    left = context.rank_positions_by_seat[seat_id]
    right = context.rank_positions_by_seat[peer_seat_id]
    return abs(left[0] - right[0]) + abs(left[1] - right[1])


def _orthogonally_adjacent(
    seat_id: str,
    peer_seat_id: str,
    *,
    context: _SeatScoreContext,
) -> bool:
    left = context.rank_positions_by_seat[seat_id]
    right = context.rank_positions_by_seat[peer_seat_id]
    same_row = left[1] == right[1] and abs(left[0] - right[0]) == 1
    same_column = left[0] == right[0] and abs(left[1] - right[1]) == 1
    return same_row or same_column


def _is_better_score(*, score: _CandidateScore, current_best: _CandidateScore | None) -> bool:
    if current_best is None:
        return True
    if score.quality > current_best.quality + QUALITY_EPSILON:
        return True
    if abs(score.quality - current_best.quality) <= QUALITY_EPSILON:
        return score.diversity > current_best.diversity + QUALITY_EPSILON
    return False
