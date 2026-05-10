"""Focused keep-near pair geometry tests for smart seating.

This module locks the tightened two-student row-layout `Keep near` contract:
left/right adjacency is the clean outcome, while across-row, diagonal, or
one-seat-buffer fallback placements remain lower-quality alternatives.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Seat
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    TeachingAnchor,
    build_seat_topology,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_candidate_scoring import (
    keep_near_has_tradeoff as _keep_near_has_tradeoff,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating_scoring import (
    keep_near_pair_score,
)

_NOW = datetime(2026, 3, 29, tzinfo=timezone.utc)


def _build_topology():
    template = RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="keep-near-geometry",
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


def test_keep_near_pair_prefers_direct_orthogonal_contact() -> None:
    topology = _build_topology()

    orthogonal_pair = topology.pair("seat-1", "seat-2")
    diagonal_pair = topology.pair("seat-1", "seat-5")

    assert orthogonal_pair.orthogonally_adjacent is True
    assert _keep_near_has_tradeoff(pair=orthogonal_pair, cluster_size=2) is False
    assert _keep_near_has_tradeoff(pair=diagonal_pair, cluster_size=2) is True
    assert keep_near_pair_score(pair=orthogonal_pair, cluster_size=2) > keep_near_pair_score(
        pair=diagonal_pair,
        cluster_size=2,
    )


def test_keep_near_pair_treats_one_seat_buffer_as_fallback_only() -> None:
    topology = _build_topology()

    orthogonal_pair = topology.pair("seat-1", "seat-4")
    buffered_pair = topology.pair("seat-1", "seat-3")

    assert buffered_pair.same_line_one_step is True
    assert _keep_near_has_tradeoff(pair=buffered_pair, cluster_size=2) is True
    assert keep_near_pair_score(pair=orthogonal_pair, cluster_size=2) > keep_near_pair_score(
        pair=buffered_pair,
        cluster_size=2,
    )
