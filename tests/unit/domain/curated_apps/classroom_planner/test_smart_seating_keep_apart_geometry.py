"""Focused keep-apart geometry tests for smart seating.

This module locks the visible seating contract for `Keep apart`: immediate
orthogonal or diagonal neighbors are invalid, while same-row or same-column
placements with one full seat buffer remain valid.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Seat
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    TeachingAnchor,
    build_seat_topology,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import (
    _keep_apart_has_tradeoff,
    _keep_apart_pair_score,
)

_NOW = datetime(2026, 3, 29, tzinfo=timezone.utc)


def _build_topology():
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="keep-apart-geometry",
        grid_cols=3,
        grid_rows=3,
        seats=[
            Seat(id="seat-1", x=0, y=0),
            Seat(id="seat-2", x=96, y=0),
            Seat(id="seat-3", x=192, y=0),
            Seat(id="seat-4", x=0, y=96),
            Seat(id="seat-5", x=96, y=96),
            Seat(id="seat-6", x=192, y=96),
            Seat(id="seat-7", x=0, y=192),
            Seat(id="seat-8", x=96, y=192),
            Seat(id="seat-9", x=192, y=192),
        ],
        fixtures=[],
        created_at=_NOW,
        updated_at=_NOW,
    )
    return build_seat_topology(
        seats=template.seats,
        anchor=TeachingAnchor(edge="top", x=96, y=0),
        fixtures=template.fixtures,
    )


def test_keep_apart_treats_immediate_diagonal_as_hard_negative() -> None:
    topology = _build_topology()

    pair = topology.pair("seat-1", "seat-5")

    assert pair.diagonal_neighbor is True
    assert _keep_apart_has_tradeoff(pair) is True
    assert _keep_apart_pair_score(pair=pair) < 0.0


def test_keep_apart_allows_same_row_with_one_full_buffer() -> None:
    topology = _build_topology()

    pair = topology.pair("seat-1", "seat-3")

    assert pair.same_row is True
    assert pair.same_line_one_step is True
    assert _keep_apart_has_tradeoff(pair) is False
    assert _keep_apart_pair_score(pair=pair) > 0.0


def test_keep_apart_allows_same_column_with_one_full_buffer() -> None:
    topology = _build_topology()

    pair = topology.pair("seat-1", "seat-7")

    assert pair.same_column is True
    assert pair.same_line_one_step is True
    assert _keep_apart_has_tradeoff(pair) is False
    assert _keep_apart_pair_score(pair=pair) > 0.0
