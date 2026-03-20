from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.curated_apps.classroom_planner.models import RoomTemplate, Seat
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.classroom_planner import RoomTemplateRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ListRoomTemplatesHandler:
    def __init__(self, templates: RoomTemplateRepositoryProtocol) -> None:
        self._templates = templates

    async def handle(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        return await self._templates.list_by_owner(owner_user_id=owner_user_id)


class GetRoomTemplateHandler:
    def __init__(self, templates: RoomTemplateRepositoryProtocol) -> None:
        self._templates = templates

    async def handle(self, *, template_id: UUID, owner_user_id: UUID) -> RoomTemplate:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))
        return template


class CreateRoomTemplateHandler:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._templates = templates
        self._clock = clock
        self._id_generator = id_generator

    async def handle(self, *, owner_user_id: UUID, name: str, seats: list[Seat]) -> RoomTemplate:
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


class UpdateRoomTemplateHandler:
    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._templates = templates
        self._clock = clock

    async def handle(
        self, *, template_id: UUID, owner_user_id: UUID, name: str, seats: list[Seat]
    ) -> RoomTemplate:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

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


class DeleteRoomTemplateHandler:
    def __init__(self, uow: UnitOfWorkProtocol, templates: RoomTemplateRepositoryProtocol) -> None:
        self._uow = uow
        self._templates = templates

    async def handle(self, *, template_id: UUID, owner_user_id: UUID) -> None:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

        async with self._uow:
            await self._templates.delete(template_id=template_id)
