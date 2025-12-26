from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    RunActiveToolCommand,
    RunActiveToolResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RunActiveToolHandler(RunActiveToolHandlerProtocol):
    """Handler for user-facing execution of published tools.

    Resolves the active version of a published tool and executes it
    in PRODUCTION context. All validation failures result in a 404
    to avoid leaking information about unpublished tools.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._execute = execute

    async def handle(
        self,
        *,
        actor: User,
        command: RunActiveToolCommand,
    ) -> RunActiveToolResult:
        async with self._uow:
            # 1. Resolve tool by slug
            tool = await self._tools.get_by_slug(slug=command.tool_slug)
            if tool is None:
                raise not_found("Tool", command.tool_slug)

            # 2. Check published state
            if not tool.is_published:
                raise not_found("Tool", command.tool_slug)

            # 3. Check active version exists (defense in depth)
            if tool.active_version_id is None:
                raise not_found("Tool", command.tool_slug)

            # 4. Fetch and validate active version
            version = await self._versions.get_by_id(version_id=tool.active_version_id)
            if version is None:
                raise not_found("Tool", command.tool_slug)
            if version.state is not VersionState.ACTIVE:
                raise not_found("Tool", command.tool_slug)

        # 5. Execute with PRODUCTION context (outside UoW - long-running)
        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=tool.id,
                version_id=version.id,
                context=RunContext.PRODUCTION,
                input_files=command.input_files,
                input_values=command.input_values,
            ),
        )
        return RunActiveToolResult(run=result.run)
