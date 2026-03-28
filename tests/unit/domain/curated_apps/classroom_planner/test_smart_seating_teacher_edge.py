"""Teacher-edge and topology smoke tests for smart seating."""

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Seat,
)
from skriptoteket.domain.curated_apps.classroom_planner.seat_topology import (
    build_seat_topology,
    infer_teaching_anchor,
)


def _template(*, fixtures: list[RoomFixture]) -> RoomTemplate:
    now = datetime(2026, 3, 27, tzinfo=timezone.utc)
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=uuid4(),
        name="Sal 101",
        grid_cols=14,
        grid_rows=9,
        seats=[
            Seat(id="seat-a", x=2, y=2),
            Seat(id="seat-b", x=6, y=2),
            Seat(id="seat-c", x=2, y=6),
            Seat(id="seat-d", x=6, y=6),
        ],
        fixtures=fixtures,
        created_at=now,
        updated_at=now,
    )


def test_infer_teaching_anchor_defaults_to_top_middle_without_cues() -> None:
    anchor = infer_teaching_anchor(template=_template(fixtures=[]))

    assert anchor.edge == "top"
    assert anchor.x == 7
    assert anchor.y == 0


def test_infer_teaching_anchor_uses_whiteboard_wall_when_present() -> None:
    anchor = infer_teaching_anchor(
        template=_template(
            fixtures=[
                RoomFixture(
                    id="fixture-1",
                    type=RoomFixtureType.WHITEBOARD,
                    x=12,
                    y=3,
                    width=1,
                    height=2,
                )
            ]
        )
    )

    assert anchor.edge == "right"
    assert anchor.x == 14
    assert anchor.y == 4


def test_build_seat_topology_respects_real_room_scale_and_aisles() -> None:
    template = _template(
        fixtures=[
            RoomFixture(
                id="fixture-1",
                type=RoomFixtureType.WHITEBOARD,
                x=2,
                y=0,
                width=8,
                height=1,
            )
        ]
    ).model_copy(
        update={
            "seats": [
                Seat(id="seat-a", x=0, y=384),
                Seat(id="seat-b", x=96, y=384),
                Seat(id="seat-c", x=192, y=384),
                Seat(id="seat-d", x=384, y=384),
                Seat(id="seat-e", x=480, y=384),
            ]
        }
    )
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    adjacent_pair = topology.pair("seat-a", "seat-b")
    aisle_pair = topology.pair("seat-c", "seat-d")

    assert adjacent_pair.orthogonally_adjacent is True
    assert adjacent_pair.same_block is True
    assert aisle_pair.orthogonally_adjacent is False
    assert aisle_pair.same_block is False


def test_build_seat_topology_groups_seats_around_the_same_table() -> None:
    template = _template(
        fixtures=[
            RoomFixture(
                id="fixture-1",
                type=RoomFixtureType.WHITEBOARD,
                x=2,
                y=0,
                width=8,
                height=1,
            ),
            RoomFixture(
                id="fixture-2",
                type=RoomFixtureType.SQUARE_TABLE,
                x=576,
                y=288,
                width=192,
                height=192,
            ),
        ]
    ).model_copy(
        update={
            "seats": [
                Seat(id="seat-left-top", x=480, y=288),
                Seat(id="seat-right-top", x=768, y=288),
                Seat(id="seat-left-bottom", x=480, y=384),
                Seat(id="seat-right-bottom", x=768, y=384),
            ]
        }
    )
    topology = build_seat_topology(
        seats=template.seats,
        anchor=infer_teaching_anchor(template=template),
        fixtures=template.fixtures,
    )

    same_table_pair = topology.pair("seat-left-top", "seat-right-top")
    assert same_table_pair.same_block is True
    assert same_table_pair.same_row is True
