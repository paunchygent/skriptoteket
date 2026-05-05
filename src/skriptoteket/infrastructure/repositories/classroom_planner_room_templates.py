"""PostgreSQL room-template repository for Klassrumskartan.

Room templates are reusable classroom layouts. The repository maps seat and
fixture JSON payloads to the room-template domain model used by drafts, Smart
seating, and exports.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import (
    RoomFixture,
    RoomFixtureType,
    RoomTemplate,
    Seat,
)
from skriptoteket.infrastructure.db.models.classroom_planner_room_template import (
    RoomTemplateModel,
)
from skriptoteket.protocols.classroom_planner import RoomTemplateRepositoryProtocol


def _to_room_template(model: RoomTemplateModel) -> RoomTemplate:
    return RoomTemplate(
        id=model.id,
        owner_user_id=model.owner_user_id,
        name=model.name,
        grid_cols=model.grid_cols,
        grid_rows=model.grid_rows,
        seats=[
            Seat(id=seat["id"], x=seat["x"], y=seat["y"], zone=seat.get("zone"))
            for seat in model.seats
        ],
        fixtures=[
            RoomFixture(
                id=fixture["id"],
                type=RoomFixtureType(fixture["type"]),
                x=fixture["x"],
                y=fixture["y"],
                width=fixture["width"],
                height=fixture["height"],
                label=fixture.get("label"),
            )
            for fixture in model.fixtures
        ],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class PostgreSQLRoomTemplateRepository(RoomTemplateRepositoryProtocol):
    """Persist classroom planner room templates in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, template_id: UUID) -> RoomTemplate | None:
        """Load one room template by id."""
        result = await self._session.execute(
            select(RoomTemplateModel).where(RoomTemplateModel.id == template_id)
        )
        model = result.scalar_one_or_none()
        return _to_room_template(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        """List room templates owned by one user."""
        result = await self._session.execute(
            select(RoomTemplateModel)
            .where(RoomTemplateModel.owner_user_id == owner_user_id)
            .order_by(RoomTemplateModel.name)
        )
        return [_to_room_template(model) for model in result.scalars().all()]

    async def save(self, *, template: RoomTemplate) -> None:
        """Insert or update one room template."""
        model = await self._session.get(RoomTemplateModel, template.id)
        if model:
            model.name = template.name
            model.grid_cols = template.grid_cols
            model.grid_rows = template.grid_rows
            model.seats = [seat.model_dump() for seat in template.seats]
            model.fixtures = [fixture.model_dump(mode="json") for fixture in template.fixtures]
            model.updated_at = template.updated_at
        else:
            model = RoomTemplateModel(
                id=template.id,
                owner_user_id=template.owner_user_id,
                name=template.name,
                grid_cols=template.grid_cols,
                grid_rows=template.grid_rows,
                seats=[seat.model_dump() for seat in template.seats],
                fixtures=[fixture.model_dump(mode="json") for fixture in template.fixtures],
                created_at=template.created_at,
                updated_at=template.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, template_id: UUID) -> None:
        """Delete one room template row."""
        await self._session.execute(
            delete(RoomTemplateModel).where(RoomTemplateModel.id == template_id)
        )
        await self._session.flush()
