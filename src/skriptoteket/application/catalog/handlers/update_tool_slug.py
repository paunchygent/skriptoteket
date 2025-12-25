from __future__ import annotations

from skriptoteket.application.catalog.commands import UpdateToolSlugCommand, UpdateToolSlugResult
from skriptoteket.domain.catalog.models import validate_tool_slug
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ToolRepositoryProtocol, UpdateToolSlugHandlerProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateToolSlugHandler(UpdateToolSlugHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._clock = clock

    async def handle(self, *, actor: User, command: UpdateToolSlugCommand) -> UpdateToolSlugResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        normalized_slug = validate_tool_slug(slug=command.slug)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            if tool.is_published:
                raise validation_error(
                    "Slug kan inte ändras efter publicering.",
                    details={"tool_id": str(tool.id)},
                )

            existing = await self._tools.get_by_slug(slug=normalized_slug)
            if existing is not None and existing.id != tool.id:
                raise validation_error(
                    f'Slug "{normalized_slug}" används redan. Välj en annan.',
                    details={"slug": normalized_slug},
                )

            if normalized_slug == tool.slug:
                return UpdateToolSlugResult(tool=tool)

            persisted = await self._tools.update_slug(
                tool_id=tool.id,
                slug=normalized_slug,
                now=now,
            )
            return UpdateToolSlugResult(tool=persisted)
