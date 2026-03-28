"""Seat-topology primitives for smart seating.

This module defines the classroom-specific geometry vocabulary used by the
smart seating solver. It turns raw seat coordinates plus the inferred teaching
edge into teacher-meaningful relations such as orthogonal adjacency, seating
blocks, and front-edge versus teaching-zone distance without introducing a
generic solver framework.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import gcd
from typing import Literal

from skriptoteket.domain.curated_apps.classroom_planner.checkpoints import (
    SeatingRoomContextSnapshot,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Seat,
)

TeachingEdge = Literal["top", "bottom", "left", "right"]
KeepNearRelationMode = Literal[
    "adjacent-row", "adjacent-column", "diagonal-block", "one-step-row", "one-step-column"
]
GEOMETRY_EPSILON = 1e-6
_SEAT_SUPPORT_FIXTURE_TYPES = frozenset(
    {RoomFixtureType.BENCH, RoomFixtureType.ROUND_TABLE, RoomFixtureType.SQUARE_TABLE}
)


@dataclass(frozen=True)
class TeachingAnchor:
    """Describe the inferred teaching/front edge and teaching zone for one room."""

    edge: TeachingEdge
    x: float
    y: float


@dataclass(frozen=True)
class _Bounds:
    max_x: float
    max_y: float


@dataclass(frozen=True)
class SeatPairTopology:
    """Describe the teacher-facing spatial relation between two seats."""

    same_row: bool
    same_column: bool
    orthogonally_adjacent: bool
    same_line_one_step: bool
    same_block: bool
    same_local_zone: bool
    front_gap: int
    lateral_gap: int
    grid_manhattan: int

    @property
    def diagonal_neighbor(self) -> bool:
        """Return whether two seats split one row and one column on the grid."""

        return not self.same_row and not self.same_column and self.grid_manhattan == 2

    @property
    def keep_near_relation_mode(self) -> KeepNearRelationMode | None:
        """Return the local compact relation mode used for keep-near rotation."""

        if self.orthogonally_adjacent and self.same_row:
            return "adjacent-row"
        if self.orthogonally_adjacent and self.same_column:
            return "adjacent-column"
        if self.diagonal_neighbor and self.same_local_zone:
            return "diagonal-block"
        if self.same_line_one_step and self.same_row:
            return "one-step-row"
        if self.same_line_one_step and self.same_column:
            return "one-step-column"
        return None


@dataclass(frozen=True)
class SeatTopology:
    """Represent the smart-seating geometry vocabulary for one room."""

    seats_by_id: dict[str, Seat]
    x_step_by_seat: dict[str, int]
    y_step_by_seat: dict[str, int]
    front_rank_by_seat: dict[str, int]
    lateral_rank_by_seat: dict[str, int]
    actual_lateral_distance_by_seat: dict[str, float]
    block_id_by_seat: dict[str, int]
    local_zone_id_by_seat: dict[str, int]
    max_front_rank: int
    min_lateral_distance: float
    max_lateral_distance: float

    def normalized_front_distance(self, seat_id: str) -> float:
        """Return the normalized band distance from the teaching edge."""

        return _normalize(
            value=float(self.front_rank_by_seat[seat_id]),
            scale=float(self.max_front_rank),
        )

    def normalized_lateral_distance(self, seat_id: str) -> float:
        """Return the normalized offset from the teaching zone along the edge."""

        return _normalize_range(
            value=self.actual_lateral_distance_by_seat[seat_id],
            minimum=self.min_lateral_distance,
            maximum=self.max_lateral_distance,
        )

    def normalized_teacher_distance(self, seat_id: str) -> float:
        """Return a front-edge-first teacher distance scalar for history fairness."""

        return (
            self.normalized_front_distance(seat_id) * 0.85
            + self.normalized_lateral_distance(seat_id) * 0.15
        )

    def near_teacher_pool(self, *, seat_count: int) -> tuple[str, ...]:
        """Return the ranked teacher-zone seat pool for near-teacher rotation."""

        if seat_count <= 0:
            return ()
        ranked_seat_ids = sorted(
            self.seats_by_id,
            key=lambda seat_id: (
                self.front_rank_by_seat[seat_id],
                self.actual_lateral_distance_by_seat[seat_id],
                self.lateral_rank_by_seat[seat_id],
                seat_id,
            ),
        )
        expanded_front_band = [
            seat_id for seat_id in ranked_seat_ids if self.front_rank_by_seat[seat_id] <= 1
        ]
        if len(expanded_front_band) >= seat_count:
            return tuple(expanded_front_band)
        return tuple(ranked_seat_ids[:seat_count])

    def pair(self, left_seat_id: str, right_seat_id: str) -> SeatPairTopology:
        """Describe the teacher-facing spatial relation between two seats."""

        left = self.seats_by_id[left_seat_id]
        right = self.seats_by_id[right_seat_id]
        horizontal_gap = abs(self.x_step_by_seat[left_seat_id] - self.x_step_by_seat[right_seat_id])
        vertical_gap = abs(self.y_step_by_seat[left_seat_id] - self.y_step_by_seat[right_seat_id])
        same_row = left.y == right.y
        same_column = left.x == right.x

        return SeatPairTopology(
            same_row=same_row,
            same_column=same_column,
            orthogonally_adjacent=(
                (same_row and horizontal_gap == 1) or (same_column and vertical_gap == 1)
            ),
            same_line_one_step=(
                (same_row and horizontal_gap == 2) or (same_column and vertical_gap == 2)
            ),
            same_block=self.block_id_by_seat[left_seat_id] == self.block_id_by_seat[right_seat_id],
            same_local_zone=self.local_zone_id_by_seat[left_seat_id]
            == self.local_zone_id_by_seat[right_seat_id],
            front_gap=abs(
                self.front_rank_by_seat[left_seat_id] - self.front_rank_by_seat[right_seat_id]
            ),
            lateral_gap=abs(
                self.lateral_rank_by_seat[left_seat_id] - self.lateral_rank_by_seat[right_seat_id]
            ),
            grid_manhattan=horizontal_gap + vertical_gap,
        )


def build_seat_topology(
    *, seats: list[Seat], anchor: TeachingAnchor, fixtures: list[RoomFixture] | None = None
) -> SeatTopology:
    """Build the smart-seating topology view for one room."""

    seats_by_id = {seat.id: seat for seat in seats}
    x_values = [seat.x for seat in seats]
    y_values = [seat.y for seat in seats]
    x_step_by_value = _axis_step_positions(x_values)
    y_step_by_value = _axis_step_positions(y_values)
    x_step_unit = _axis_step_unit(sorted(set(x_values)))
    y_step_unit = _axis_step_unit(sorted(set(y_values)))
    x_step_by_seat = {seat.id: x_step_by_value[seat.x] for seat in seats}
    y_step_by_seat = {seat.id: y_step_by_value[seat.y] for seat in seats}
    seat_id_by_step_position = {
        (x_step_by_seat[seat.id], y_step_by_seat[seat.id]): seat.id for seat in seats
    }
    max_row_rank = max(y_step_by_value.values(), default=0)
    max_column_rank = max(x_step_by_value.values(), default=0)

    front_rank_by_seat: dict[str, int] = {}
    lateral_rank_by_seat: dict[str, int] = {}
    actual_lateral_distance_by_seat: dict[str, float] = {}

    for seat in seats:
        if anchor.edge == "top":
            front_rank_by_seat[seat.id] = y_step_by_seat[seat.id]
            lateral_rank_by_seat[seat.id] = x_step_by_seat[seat.id]
            actual_lateral_distance_by_seat[seat.id] = abs(seat.x - anchor.x)
            continue
        if anchor.edge == "bottom":
            front_rank_by_seat[seat.id] = max_row_rank - y_step_by_seat[seat.id]
            lateral_rank_by_seat[seat.id] = x_step_by_seat[seat.id]
            actual_lateral_distance_by_seat[seat.id] = abs(seat.x - anchor.x)
            continue
        if anchor.edge == "left":
            front_rank_by_seat[seat.id] = x_step_by_seat[seat.id]
            lateral_rank_by_seat[seat.id] = y_step_by_seat[seat.id]
            actual_lateral_distance_by_seat[seat.id] = abs(seat.y - anchor.y)
            continue
        front_rank_by_seat[seat.id] = max_column_rank - x_step_by_seat[seat.id]
        lateral_rank_by_seat[seat.id] = y_step_by_seat[seat.id]
        actual_lateral_distance_by_seat[seat.id] = abs(seat.y - anchor.y)

    return SeatTopology(
        seats_by_id=seats_by_id,
        x_step_by_seat=x_step_by_seat,
        y_step_by_seat=y_step_by_seat,
        front_rank_by_seat=front_rank_by_seat,
        lateral_rank_by_seat=lateral_rank_by_seat,
        actual_lateral_distance_by_seat=actual_lateral_distance_by_seat,
        block_id_by_seat=_build_block_ids(
            seats,
            fixtures=fixtures or [],
            x_step_by_seat=x_step_by_seat,
            y_step_by_seat=y_step_by_seat,
            x_step_unit=x_step_unit,
            y_step_unit=y_step_unit,
        ),
        local_zone_id_by_seat=_connected_component_ids(
            seats=seats,
            seat_id_by_step_position=seat_id_by_step_position,
            x_step_by_seat=x_step_by_seat,
            y_step_by_seat=y_step_by_seat,
        ),
        max_front_rank=max(front_rank_by_seat.values(), default=0),
        min_lateral_distance=min(actual_lateral_distance_by_seat.values(), default=0.0),
        max_lateral_distance=max(actual_lateral_distance_by_seat.values(), default=0.0),
    )


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


def _build_block_ids(
    seats: list[Seat],
    *,
    fixtures: list[RoomFixture],
    x_step_by_seat: dict[str, int],
    y_step_by_seat: dict[str, int],
    x_step_unit: int,
    y_step_unit: int,
) -> dict[str, int]:
    block_id_by_seat = _fixture_block_ids(
        seats=seats,
        fixtures=fixtures,
        x_step_unit=x_step_unit,
        y_step_unit=y_step_unit,
    )
    next_block_id = max(block_id_by_seat.values(), default=-1) + 1

    for seat in seats:
        if seat.id in block_id_by_seat:
            continue
        for current_id, component_id in _connected_component_ids(
            seats=[seat],
            seat_id_by_step_position={
                (x_step_by_seat[candidate.id], y_step_by_seat[candidate.id]): candidate.id
                for candidate in seats
            },
            x_step_by_seat=x_step_by_seat,
            y_step_by_seat=y_step_by_seat,
        ).items():
            if component_id == 0 and current_id not in block_id_by_seat:
                block_id_by_seat[current_id] = next_block_id
        next_block_id += 1

    return block_id_by_seat


def _connected_component_ids(
    *,
    seats: list[Seat],
    seat_id_by_step_position: dict[tuple[int, int], str],
    x_step_by_seat: dict[str, int],
    y_step_by_seat: dict[str, int],
) -> dict[str, int]:
    component_id_by_seat: dict[str, int] = {}
    next_component_id = 0
    for seat in seats:
        if seat.id in component_id_by_seat:
            continue
        queue = deque([seat.id])
        while queue:
            current_id = queue.popleft()
            if current_id in component_id_by_seat:
                continue
            component_id_by_seat[current_id] = next_component_id
            for neighbor_id in _orthogonal_neighbor_ids(
                seat_id=current_id,
                seat_id_by_step_position=seat_id_by_step_position,
                x_step_by_seat=x_step_by_seat,
                y_step_by_seat=y_step_by_seat,
            ):
                if neighbor_id not in component_id_by_seat:
                    queue.append(neighbor_id)
        next_component_id += 1
    return component_id_by_seat


def _fixture_block_ids(
    *, seats: list[Seat], fixtures: list[RoomFixture], x_step_unit: int, y_step_unit: int
) -> dict[str, int]:
    fixture_group_key_by_id = _fixture_group_keys(fixtures)
    fixture_block_id_by_key: dict[str, int] = {}
    block_id_by_seat: dict[str, int] = {}
    max_fixture_gap = float(max(x_step_unit, y_step_unit))
    support_fixtures = [
        fixture for fixture in fixtures if fixture.type in _SEAT_SUPPORT_FIXTURE_TYPES
    ]
    for seat in seats:
        candidates = [
            (_distance_to_fixture(seat=seat, fixture=fixture), fixture.id)
            for fixture in support_fixtures
        ]
        if not candidates:
            continue
        distance, fixture_id = min(candidates)
        if distance > max_fixture_gap + GEOMETRY_EPSILON:
            continue
        group_key = fixture_group_key_by_id[fixture_id]
        block_id_by_seat[seat.id] = fixture_block_id_by_key.setdefault(
            group_key, len(fixture_block_id_by_key)
        )
    return block_id_by_seat


def _fixture_group_keys(fixtures: list[RoomFixture]) -> dict[str, str]:
    group_key_by_id = {
        fixture.id: fixture.id
        for fixture in fixtures
        if fixture.type in _SEAT_SUPPORT_FIXTURE_TYPES
    }
    bench_rows: dict[int, list[RoomFixture]] = {}
    for fixture in fixtures:
        if fixture.type is RoomFixtureType.BENCH:
            bench_rows.setdefault(fixture.y, []).append(fixture)
    for row_y, row_fixtures in bench_rows.items():
        previous_right = -1
        group_key = ""
        for fixture in sorted(row_fixtures, key=lambda item: item.x):
            if fixture.x > previous_right:
                group_key = f"bench-row:{row_y}:{fixture.x}"
            group_key_by_id[fixture.id] = group_key
            previous_right = fixture.x + fixture.width
    return group_key_by_id


def _orthogonal_neighbor_ids(
    *,
    seat_id: str,
    seat_id_by_step_position: dict[tuple[int, int], str],
    x_step_by_seat: dict[str, int],
    y_step_by_seat: dict[str, int],
) -> list[str]:
    neighbors: list[str] = []
    seat_x = x_step_by_seat[seat_id]
    seat_y = y_step_by_seat[seat_id]
    for delta_x, delta_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        neighbor_id = seat_id_by_step_position.get((seat_x + delta_x, seat_y + delta_y))
        if neighbor_id is None:
            continue
        neighbors.append(neighbor_id)
    return neighbors


def _distance_to_fixture(*, seat: Seat, fixture: RoomFixture) -> float:
    dx = max(float(fixture.x - seat.x), 0.0, float(seat.x - (fixture.x + fixture.width)))
    dy = max(float(fixture.y - seat.y), 0.0, float(seat.y - (fixture.y + fixture.height)))
    return max(dx, dy)


def _axis_step_positions(values: list[int]) -> dict[int, int]:
    unique_values = sorted(set(values))
    if not unique_values:
        return {}

    step_unit = _axis_step_unit(unique_values)
    origin = unique_values[0]
    return {
        value: int(round((value - origin) / step_unit)) if step_unit > 0 else 0
        for value in unique_values
    }


def _axis_step_unit(values: list[int]) -> int:
    positive_gaps = [
        right_value - left_value
        for left_value, right_value in zip(values, values[1:], strict=False)
        if right_value > left_value
    ]
    if not positive_gaps:
        return 1

    step_unit = positive_gaps[0]
    for gap in positive_gaps[1:]:
        step_unit = gcd(step_unit, gap)
    return max(step_unit, 1)


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


def _best_wall(*, fixtures: list[RoomFixture], bounds: _Bounds) -> TeachingEdge:
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
            if abs(distance - nearest_distance) <= GEOMETRY_EPSILON:
                scores[wall] += 1.0
            scores[wall] -= distance * 0.01
    winning_wall = max(scores.items(), key=lambda item: (item[1], item[0]))[0]
    return winning_wall  # type: ignore[return-value]


def _fixture_center(fixture: RoomFixture) -> tuple[float, float]:
    return (fixture.x + fixture.width / 2, fixture.y + fixture.height / 2)


def _mix(center_value: float, cue_value: float, cue_weight: float) -> float:
    return center_value * (1 - cue_weight) + cue_value * cue_weight


def _normalize(*, value: float, scale: float) -> float:
    if scale <= 0:
        return 0.0
    return value / scale


def _normalize_range(*, value: float, minimum: float, maximum: float) -> float:
    scale = maximum - minimum
    if scale <= 0:
        return 0.0
    return (value - minimum) / scale
