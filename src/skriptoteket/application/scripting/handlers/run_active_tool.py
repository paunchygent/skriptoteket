from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    RunActiveToolCommand,
    RunActiveToolResult,
    SessionFilesMode,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    RunActiveToolHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
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
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._execute = execute
        self._sessions = sessions
        self._id_generator = id_generator
        self._session_files = session_files

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

        session_context = normalize_tool_session_context(context=command.session_context)
        input_files = list(command.input_files)

        if not input_files and command.session_files_mode is SessionFilesMode.REUSE:
            input_files = await self._session_files.get_files(
                tool_id=tool.id,
                user_id=actor.id,
                context=session_context,
            )
        elif not input_files and command.session_files_mode is SessionFilesMode.CLEAR:
            await self._session_files.clear_session(
                tool_id=tool.id,
                user_id=actor.id,
                context=session_context,
            )

        # 5. Execute with PRODUCTION context (outside UoW - long-running)
        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=tool.id,
                version_id=version.id,
                context=RunContext.PRODUCTION,
                input_files=input_files,
                input_values=command.input_values,
            ),
        )

        # Persist session-scoped files for subsequent action runs (ADR-0039).
        if command.input_files:
            await self._session_files.store_files(
                tool_id=tool.id,
                user_id=actor.id,
                context=session_context,
                files=command.input_files,
            )

        # Persist normalized session state after the initial run when next_actions exist (ADR-0024).
        run = result.run
        if run.ui_payload is not None and run.ui_payload.next_actions:
            async with self._uow:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=tool.id,
                    user_id=actor.id,
                    context=session_context,
                )
                await self._sessions.update_state(
                    tool_id=tool.id,
                    user_id=actor.id,
                    context=session_context,
                    expected_state_rev=session.state_rev,
                    state=result.normalized_state,
                )

        return RunActiveToolResult(run=run)
