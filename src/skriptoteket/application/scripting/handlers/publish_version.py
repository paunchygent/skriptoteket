from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    PublishVersionCommand,
    PublishVersionResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import publish_version
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    PublishVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class PublishVersionHandler(PublishVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: PublishVersionCommand,
    ) -> PublishVersionResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        new_active_version_id = self._id_generator.new_uuid()
        change_summary = (
            command.change_summary.strip()
            if command.change_summary is not None and command.change_summary.strip()
            else None
        )

        async with self._uow:
            reviewed_version = await self._versions.get_by_id(version_id=command.version_id)
            if reviewed_version is None:
                raise not_found("ToolVersion", str(command.version_id))

            tool = await self._tools.get_by_id(tool_id=reviewed_version.tool_id)
            if tool is None:
                raise not_found("Tool", str(reviewed_version.tool_id))

            previous_active_version = await self._versions.get_active_for_tool(
                tool_id=reviewed_version.tool_id
            )
            new_active_version_number = await self._versions.get_next_version_number(
                tool_id=reviewed_version.tool_id
            )

            result = publish_version(
                reviewed_version=reviewed_version,
                new_active_version_id=new_active_version_id,
                new_active_version_number=new_active_version_number,
                published_by_user_id=actor.id,
                now=now,
                change_summary=change_summary,
                previous_active_version=previous_active_version,
            )

            archived_previous_active = None
            if result.archived_previous_active_version is not None:
                archived_previous_active = await self._versions.update(
                    version=result.archived_previous_active_version
                )

            archived_reviewed = await self._versions.update(
                version=result.archived_reviewed_version
            )
            new_active = await self._versions.create(version=result.new_active_version)
            await self._tools.set_active_version_id(
                tool_id=tool.id,
                active_version_id=new_active.id,
                now=now,
            )
            if not tool.is_published:
                await self._tools.set_published(
                    tool_id=tool.id,
                    is_published=True,
                    now=now,
                )

        return PublishVersionResult(
            new_active_version=new_active,
            archived_reviewed_version=archived_reviewed,
            archived_previous_active_version=archived_previous_active,
        )
