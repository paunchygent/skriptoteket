"""Application services for the Classroom Planner curated app."""

from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.apps.classroom_planner.models import (
    ClassroomPlannerBootstrapPayload,
    LessonModePreset,
    RoomTemplate,
    Roster,
    Seat,
    Student,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.classroom_planner import (
    RoomTemplateRepositoryProtocol,
    RosterRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

# Standard presets (per ADR-0069 decision to bootstrap from catalog)
LESSON_MODES = [
    LessonModePreset(id="standard", name="Standard Lektion"),
    LessonModePreset(id="test", name="Prov/Examination"),
    LessonModePreset(id="group_work", name="Grupparbete"),
    LessonModePreset(id="lab", name="Laboration"),
]


class ClassroomPlannerBootstrapService:
    """Service to handle bootstrapping tasks for the Classroom Planner app."""

    def __init__(self) -> None:
        pass

    async def get_bootstrap_payload(
        self, *, owner_user_id: UUID
    ) -> ClassroomPlannerBootstrapPayload:
        """Returns the initial payload for app initialization."""
        return ClassroomPlannerBootstrapPayload(
            lesson_modes=LESSON_MODES,
            feature_flags={
                "solver_v1": False,
                "multi_room_support": False,
            },
        )


class ClassroomPlannerService:
    """Service for managing classroom planner entities (Rosters, Templates)."""

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        rosters: RosterRepositoryProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._rosters = rosters
        self._templates = templates
        self._clock = clock
        self._id_generator = id_generator

    # Roster CRUD

    async def list_rosters(self, *, owner_user_id: UUID) -> list[Roster]:
        return await self._rosters.list_by_owner(owner_user_id=owner_user_id)

    async def get_roster(self, *, roster_id: UUID, owner_user_id: UUID) -> Roster:
        roster = await self._rosters.get_by_id(roster_id=roster_id)
        if not roster or roster.owner_user_id != owner_user_id:
            raise not_found("Roster", str(roster_id))
        return roster

    async def create_roster(
        self, *, owner_user_id: UUID, name: str, students: list[Student]
    ) -> Roster:
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

    async def update_roster(
        self, *, roster_id: UUID, owner_user_id: UUID, name: str, students: list[Student]
    ) -> Roster:
        roster = await self.get_roster(roster_id=roster_id, owner_user_id=owner_user_id)
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

    async def delete_roster(self, *, roster_id: UUID, owner_user_id: UUID) -> None:
        # Ensure it exists and belongs to the user
        await self.get_roster(roster_id=roster_id, owner_user_id=owner_user_id)
        async with self._uow:
            await self._rosters.delete(roster_id=roster_id)

    # RoomTemplate CRUD

    async def list_templates(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        return await self._templates.list_by_owner(owner_user_id=owner_user_id)

    async def get_template(self, *, template_id: UUID, owner_user_id: UUID) -> RoomTemplate:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))
        return template

    async def create_template(
        self, *, owner_user_id: UUID, name: str, seats: list[Seat]
    ) -> RoomTemplate:
        now = self._clock.now()
        template = RoomTemplate(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            name=name,
            seats=seats,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._templates.save(template=template)
        return template

    async def update_template(
        self, *, template_id: UUID, owner_user_id: UUID, name: str, seats: list[Seat]
    ) -> RoomTemplate:
        template = await self.get_template(template_id=template_id, owner_user_id=owner_user_id)
        updated = RoomTemplate(
            id=template.id,
            owner_user_id=template.owner_user_id,
            name=name,
            seats=seats,
            created_at=template.created_at,
            updated_at=self._clock.now(),
        )
        async with self._uow:
            await self._templates.save(template=updated)
        return updated

    async def delete_template(self, *, template_id: UUID, owner_user_id: UUID) -> None:
        # Ensure it exists and belongs to the user
        await self.get_template(template_id=template_id, owner_user_id=owner_user_id)
        async with self._uow:
            await self._templates.delete(template_id=template_id)
