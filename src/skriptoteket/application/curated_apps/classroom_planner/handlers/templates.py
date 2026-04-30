"""Room template handlers for the classroom planner curated app.

This module owns CRUD for reusable classroom layouts. It validates seat and
fixture identities so the planner can render visually rich room canvases with
stable references for later PDF/XLSX export work.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.handlers.share_artifacts import (
    ClassroomPlannerShareLifecycleService,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DEFAULT_ROOM_GRID_COLS,
    DEFAULT_ROOM_GRID_ROWS,
    RoomFixture,
    RoomTemplate,
    Seat,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.classroom_planner import (
    PlanDraftRepositoryProtocol,
    RoomTemplateRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _validate_template(*, seats: list[Seat], fixtures: list[RoomFixture]) -> None:
    duplicate_seat_ids = [
        seat_id for seat_id, count in Counter(s.id for s in seats).items() if count > 1
    ]
    duplicate_fixture_ids = [
        fixture_id for fixture_id, count in Counter(f.id for f in fixtures).items() if count > 1
    ]
    if duplicate_seat_ids:
        raise validation_error(
            "Seat IDs must be unique within a room template.",
            details={"duplicate_seat_ids": duplicate_seat_ids},
        )
    if duplicate_fixture_ids:
        raise validation_error(
            "Fixture IDs must be unique within a room template.",
            details={"duplicate_fixture_ids": duplicate_fixture_ids},
        )


class ListRoomTemplatesHandler:
    """List room templates owned by the current user."""

    def __init__(self, templates: RoomTemplateRepositoryProtocol) -> None:
        self._templates = templates

    async def handle(self, *, owner_user_id: UUID) -> list[RoomTemplate]:
        return await self._templates.list_by_owner(owner_user_id=owner_user_id)


class GetRoomTemplateHandler:
    """Load one room template owned by the current user."""

    def __init__(self, templates: RoomTemplateRepositoryProtocol) -> None:
        self._templates = templates

    async def handle(self, *, template_id: UUID, owner_user_id: UUID) -> RoomTemplate:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))
        return template


class CreateRoomTemplateHandler:
    """Create a reusable room template asset."""

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

    async def handle(
        self,
        *,
        owner_user_id: UUID,
        name: str,
        grid_cols: int = DEFAULT_ROOM_GRID_COLS,
        grid_rows: int = DEFAULT_ROOM_GRID_ROWS,
        seats: list[Seat],
        fixtures: list[RoomFixture],
    ) -> RoomTemplate:
        _validate_template(seats=seats, fixtures=fixtures)
        now = self._clock.now()
        template = RoomTemplate(
            id=self._id_generator.new_uuid(),
            owner_user_id=owner_user_id,
            name=name,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            seats=seats,
            fixtures=fixtures,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            await self._templates.save(template=template)
        return template


class UpdateRoomTemplateHandler:
    """Update a reusable room template asset."""

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
        self,
        *,
        template_id: UUID,
        owner_user_id: UUID,
        name: str,
        grid_cols: int = DEFAULT_ROOM_GRID_COLS,
        grid_rows: int = DEFAULT_ROOM_GRID_ROWS,
        seats: list[Seat],
        fixtures: list[RoomFixture],
    ) -> RoomTemplate:
        _validate_template(seats=seats, fixtures=fixtures)
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

        updated = RoomTemplate(
            id=template.id,
            owner_user_id=template.owner_user_id,
            name=name,
            grid_cols=grid_cols,
            grid_rows=grid_rows,
            seats=seats,
            fixtures=fixtures,
            created_at=template.created_at,
            updated_at=self._clock.now(),
        )
        async with self._uow:
            await self._templates.save(template=updated)
        return updated


class DeleteRoomTemplateHandler:
    """Delete a room template and every dependent planner draft."""

    def __init__(
        self,
        uow: UnitOfWorkProtocol,
        templates: RoomTemplateRepositoryProtocol,
        drafts: PlanDraftRepositoryProtocol,
        share_lifecycle: ClassroomPlannerShareLifecycleService | None = None,
    ) -> None:
        self._uow = uow
        self._templates = templates
        self._drafts = drafts
        self._share_lifecycle = share_lifecycle

    async def handle(self, *, template_id: UUID, owner_user_id: UUID) -> None:
        template = await self._templates.get_by_id(template_id=template_id)
        if not template or template.owner_user_id != owner_user_id:
            raise not_found("RoomTemplate", str(template_id))

        async with self._uow:
            if self._share_lifecycle is not None:
                await self._share_lifecycle.revoke_for_template_delete(
                    owner_user_id=owner_user_id,
                    template_id=template_id,
                )
            await self._drafts.delete_for_template(
                owner_user_id=owner_user_id,
                template_id=template_id,
            )
            await self._templates.delete(template_id=template_id)
