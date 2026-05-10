"""Seat-support context for Klassrumskartan smart seating.

Purpose:
    Classify seats by their supporting classroom furniture so solver scoring
    and rule diagnostics can distinguish table, bench-row, and plain row
    layouts without duplicating geometry rules in the frontend.

Relationships:
    - Consumes raw room fixtures plus `SeatTopology` output.
    - Feeds smart seating scoring and solver-owned rule diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from typing import Literal

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomFixtureType,
    Seat,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    GEOMETRY_EPSILON,
    SeatPairTopology,
    SeatTopology,
    TeachingAnchor,
)

SeatingContext = Literal["shared_table", "bench_row", "row_layout", "local_cluster", "unknown"]

_TABLE_TYPES = frozenset({RoomFixtureType.ROUND_TABLE, RoomFixtureType.SQUARE_TABLE})
_SUPPORT_TYPES = frozenset({*_TABLE_TYPES, RoomFixtureType.BENCH})


@dataclass(frozen=True)
class SeatSupportContext:
    """Expose seat support grouping and teacher-proximity table ranks."""

    group_key_by_seat_id: dict[str, str]
    context_by_group_key: dict[str, SeatingContext]
    table_rank_by_group_key: dict[str, int]

    def seat_context(self, seat_id: str) -> SeatingContext:
        """Return the strongest known individual support context for one seat."""

        group_key = self.group_key_by_seat_id.get(seat_id)
        if group_key is None:
            return "row_layout"
        return self.context_by_group_key.get(group_key, "unknown")

    def pair_context(
        self,
        *,
        left_seat_id: str,
        right_seat_id: str,
        pair: SeatPairTopology,
    ) -> SeatingContext:
        """Return the context that should govern one pair relationship."""

        left_group = self.group_key_by_seat_id.get(left_seat_id)
        right_group = self.group_key_by_seat_id.get(right_seat_id)
        if left_group is not None and left_group == right_group:
            return self.context_by_group_key.get(left_group, "unknown")
        if (
            self.seat_context(left_seat_id) == "row_layout"
            and self.seat_context(right_seat_id) == "row_layout"
        ):
            return "row_layout"
        if pair.same_local_zone:
            return "local_cluster"
        return "unknown"

    def table_rank(self, seat_id: str) -> int | None:
        """Return the teacher-proximity rank for the seat's table group."""

        group_key = self.group_key_by_seat_id.get(seat_id)
        if group_key is None or self.context_by_group_key.get(group_key) != "shared_table":
            return None
        return self.table_rank_by_group_key.get(group_key)


def build_seat_support_context(
    *,
    seats: list[Seat],
    fixtures: list[RoomFixture],
    anchor: TeachingAnchor,
) -> SeatSupportContext:
    """Build furniture-aware context for smart seating semantics."""

    fixture_group_key_by_id = _fixture_group_keys(fixtures)
    context_by_group_key = _context_by_group_key(fixtures, fixture_group_key_by_id)
    group_key_by_seat_id = _seat_support_groups(
        seats=seats,
        fixtures=fixtures,
        fixture_group_key_by_id=fixture_group_key_by_id,
    )
    return SeatSupportContext(
        group_key_by_seat_id=group_key_by_seat_id,
        context_by_group_key=context_by_group_key,
        table_rank_by_group_key=_table_group_ranks(
            fixtures=fixtures,
            fixture_group_key_by_id=fixture_group_key_by_id,
            context_by_group_key=context_by_group_key,
            anchor=anchor,
        ),
    )


def desired_near_teacher_seat_ids(
    *, topology: SeatTopology, support_context: SeatSupportContext
) -> tuple[str, ...]:
    """Return backend-owned seats that satisfy `Nära läraren`."""

    return tuple(
        sorted(
            seat_id
            for seat_id in topology.seats_by_id
            if _near_teacher_band(
                seat_id=seat_id,
                topology=topology,
                support_context=support_context,
            )
            == "desired"
        )
    )


def near_teacher_band(
    *,
    seat_id: str,
    topology: SeatTopology,
    support_context: SeatSupportContext,
) -> Literal["desired", "degraded", "failed"]:
    """Classify one seat against the backend-owned near-teacher contract."""

    return _near_teacher_band(
        seat_id=seat_id,
        topology=topology,
        support_context=support_context,
    )


def _near_teacher_band(
    *,
    seat_id: str,
    topology: SeatTopology,
    support_context: SeatSupportContext,
) -> Literal["desired", "degraded", "failed"]:
    table_rank = support_context.table_rank(seat_id)
    if table_rank is not None:
        if table_rank <= 1:
            return "desired"
        if table_rank == 2:
            return "degraded"
        return "failed"
    front_rank = topology.front_rank_by_seat[seat_id]
    local_front_rank = _local_zone_front_rank(seat_id=seat_id, topology=topology)
    if front_rank == local_front_rank:
        return "desired"
    if front_rank == local_front_rank + 1:
        return "degraded"
    return "failed"


def _local_zone_front_rank(*, seat_id: str, topology: SeatTopology) -> int:
    local_zone_id = topology.local_zone_id_by_seat[seat_id]
    return min(
        topology.front_rank_by_seat[other_seat_id]
        for other_seat_id, other_zone_id in topology.local_zone_id_by_seat.items()
        if other_zone_id == local_zone_id
    )


def _seat_support_groups(
    *,
    seats: list[Seat],
    fixtures: list[RoomFixture],
    fixture_group_key_by_id: dict[str, str],
) -> dict[str, str]:
    support_fixtures = [fixture for fixture in fixtures if fixture.type in _SUPPORT_TYPES]
    if not support_fixtures:
        return {}
    x_step_unit = _axis_step_unit(sorted({seat.x for seat in seats}))
    y_step_unit = _axis_step_unit(sorted({seat.y for seat in seats}))
    max_fixture_gap = float(max(x_step_unit, y_step_unit))
    group_key_by_seat_id: dict[str, str] = {}
    for seat in seats:
        distance, fixture_id = min(
            (_distance_to_fixture(seat=seat, fixture=fixture), fixture.id)
            for fixture in support_fixtures
        )
        if distance <= max_fixture_gap + GEOMETRY_EPSILON:
            group_key_by_seat_id[seat.id] = fixture_group_key_by_id[fixture_id]
    return group_key_by_seat_id


def _fixture_group_keys(fixtures: list[RoomFixture]) -> dict[str, str]:
    group_key_by_id = {
        fixture.id: fixture.id for fixture in fixtures if fixture.type in _SUPPORT_TYPES
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


def _context_by_group_key(
    fixtures: list[RoomFixture], fixture_group_key_by_id: dict[str, str]
) -> dict[str, SeatingContext]:
    context_by_key: dict[str, SeatingContext] = {}
    for fixture in fixtures:
        group_key = fixture_group_key_by_id.get(fixture.id)
        if group_key is None:
            continue
        context_by_key[group_key] = "shared_table" if fixture.type in _TABLE_TYPES else "bench_row"
    return context_by_key


def _table_group_ranks(
    *,
    fixtures: list[RoomFixture],
    fixture_group_key_by_id: dict[str, str],
    context_by_group_key: dict[str, SeatingContext],
    anchor: TeachingAnchor,
) -> dict[str, int]:
    table_groups = {
        group_key
        for group_key, context in context_by_group_key.items()
        if context == "shared_table"
    }
    ranked_group_keys = sorted(
        table_groups,
        key=lambda group_key: min(
            _fixture_anchor_rank(fixture=fixture, anchor=anchor)
            for fixture in fixtures
            if fixture_group_key_by_id.get(fixture.id) == group_key
        ),
    )
    return {group_key: index for index, group_key in enumerate(ranked_group_keys)}


def _fixture_anchor_rank(
    *, fixture: RoomFixture, anchor: TeachingAnchor
) -> tuple[float, float, str]:
    center_x = fixture.x + fixture.width / 2
    center_y = fixture.y + fixture.height / 2
    if anchor.edge == "top":
        return (float(fixture.y), abs(center_x - anchor.x), fixture.id)
    if anchor.edge == "bottom":
        return (
            abs(anchor.y - (fixture.y + fixture.height)),
            abs(center_x - anchor.x),
            fixture.id,
        )
    if anchor.edge == "left":
        return (float(fixture.x), abs(center_y - anchor.y), fixture.id)
    return (
        abs(anchor.x - (fixture.x + fixture.width)),
        abs(center_y - anchor.y),
        fixture.id,
    )


def _distance_to_fixture(*, seat: Seat, fixture: RoomFixture) -> float:
    dx = max(float(fixture.x - seat.x), 0.0, float(seat.x - (fixture.x + fixture.width)))
    dy = max(float(fixture.y - seat.y), 0.0, float(seat.y - (fixture.y + fixture.height)))
    return max(dx, dy)


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
