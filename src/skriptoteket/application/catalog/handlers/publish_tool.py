from __future__ import annotations

from skriptoteket.application.catalog.commands import PublishToolCommand, PublishToolResult
from skriptoteket.application.catalog.publish_requirements import (
    ensure_tool_publish_requirements,
)
from skriptoteket.domain.catalog.models import set_tool_published_state
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.protocols.catalog import PublishToolHandlerProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class PublishToolHandler(PublishToolHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._clock = clock

    async def handle(self, *, actor: User, command: PublishToolCommand) -> PublishToolResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()
        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            if tool.is_published:
                return PublishToolResult(tool=tool)

            if tool.active_version_id is None:
                raise validation_error(
                    "Tool has no active script version and cannot be published",
                    details={"tool_id": str(tool.id)},
                )

            await ensure_tool_publish_requirements(
                tool=tool,
                list_tag_ids=self._tools.list_tag_ids,
            )

            version = await self._versions.get_by_id(version_id=tool.active_version_id)
            if version is None:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Tool active_version_id points to a missing tool version",
                    details={
                        "tool_id": str(tool.id),
                        "active_version_id": str(tool.active_version_id),
                    },
                )
            if version.tool_id != tool.id:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Tool active_version_id points to a version for a different tool",
                    details={
                        "tool_id": str(tool.id),
                        "active_version_id": str(tool.active_version_id),
                        "version_tool_id": str(version.tool_id),
                    },
                )
            if version.state is not VersionState.ACTIVE:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Tool active_version_id must point to an ACTIVE tool version",
                    details={
                        "tool_id": str(tool.id),
                        "active_version_id": str(tool.active_version_id),
                        "state": version.state.value,
                    },
                )

            updated_tool = set_tool_published_state(tool=tool, is_published=True, now=now)
            if updated_tool is tool:
                return PublishToolResult(tool=tool)

            persisted = await self._tools.set_published(
                tool_id=tool.id,
                is_published=True,
                now=now,
            )
            return PublishToolResult(tool=persisted)
