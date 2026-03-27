"""Pure teacher-edge inference tests for smart seating."""

from datetime import datetime, timezone
from uuid import uuid4

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Seat,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_seating import infer_teaching_anchor


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


def test_infer_teaching_anchor_softens_teacher_desk_offset_toward_room_center() -> None:
    anchor = infer_teaching_anchor(
        template=_template(
            fixtures=[
                RoomFixture(
                    id="fixture-1",
                    type=RoomFixtureType.TEACHER_DESK,
                    x=10,
                    y=0,
                    width=2,
                    height=1,
                )
            ]
        )
    )

    assert anchor.edge == "top"
    assert 7 < anchor.x < 11
    assert anchor.y == 0
