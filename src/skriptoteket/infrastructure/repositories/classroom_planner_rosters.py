"""PostgreSQL roster repository for Klassrumskartan.

Rosters are teacher-owned class-list assets. The repository maps roster rows to
the roster domain model and stores student identity/display-name payloads as the
current JSON contract.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.curated_apps.classroom_planner.models import Roster, Student
from skriptoteket.infrastructure.db.models.classroom_planner_roster import RosterModel
from skriptoteket.protocols.classroom_planner import RosterRepositoryProtocol


def _to_roster(model: RosterModel) -> Roster:
    return Roster(
        id=model.id,
        owner_user_id=model.owner_user_id,
        name=model.name,
        students=[
            Student(id=student["id"], display_name=student["display_name"])
            for student in model.students
        ],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class PostgreSQLRosterRepository(RosterRepositoryProtocol):
    """Persist classroom planner rosters in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, roster_id: UUID) -> Roster | None:
        """Load one roster by id."""
        result = await self._session.execute(select(RosterModel).where(RosterModel.id == roster_id))
        model = result.scalar_one_or_none()
        return _to_roster(model) if model else None

    async def list_by_owner(self, *, owner_user_id: UUID) -> list[Roster]:
        """List rosters owned by one user."""
        result = await self._session.execute(
            select(RosterModel)
            .where(RosterModel.owner_user_id == owner_user_id)
            .order_by(RosterModel.name)
        )
        return [_to_roster(model) for model in result.scalars().all()]

    async def save(self, *, roster: Roster) -> None:
        """Insert or update one roster."""
        model = await self._session.get(RosterModel, roster.id)
        if model:
            model.name = roster.name
            model.students = [student.model_dump() for student in roster.students]
            model.updated_at = roster.updated_at
        else:
            model = RosterModel(
                id=roster.id,
                owner_user_id=roster.owner_user_id,
                name=roster.name,
                students=[student.model_dump() for student in roster.students],
                created_at=roster.created_at,
                updated_at=roster.updated_at,
            )
            self._session.add(model)
        await self._session.flush()

    async def delete(self, *, roster_id: UUID) -> None:
        """Delete one roster row."""
        await self._session.execute(delete(RosterModel).where(RosterModel.id == roster_id))
        await self._session.flush()
