from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import Roster, Student
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.classroom_planner import RosterRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ListRostersHandler:
    def __init__(self, rosters: RosterRepositoryProtocol) -> None:
        self._rosters = rosters

    async def handle(self, *, owner_user_id: UUID) -> list[Roster]:
        return await self._rosters.list_by_owner(owner_user_id=owner_user_id)


class GetRosterHandler:
    def __init__(self, rosters: RosterRepositoryProtocol) -> None:
        self._rosters = rosters

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> Roster:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        return roster


class CreateRosterHandler:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, owner_user_id: UUID, name: str, students: list[Student]) -> Roster:
        now = self._clock.now()
        roster = Roster(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            name=name,
            students=students,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._rosters.save(roster=roster)
        return roster


class UpdateRosterHandler:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._clock = clock

    async def handle(
        self, *, roster_id: UUID, owner_user_id: UUID, name: str, students: list[Student]
    ) -> Roster:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        updated = Roster(
            id=roster.id,
            owner_user_id=roster.owner_user_id,
            name=name,
            students=students,
            created_at=roster.created_at,
            updated_at=self._clock.now(),
        )
        async with self._uow:
            await self._rosters.save(roster=updated)
        return updated


class DeleteRosterHandler:
    def __init__(self, uow: UnitOfWorkProtocol, rosters: RosterRepositoryProtocol) -> None:
        self._uow = uow
        self._rosters = rosters

    async def handle(self, *, roster_id: UUID, owner_user_id: UUID) -> None:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))

        async with self._uow:
            await self._rosters.delete(roster_id=roster_id)
