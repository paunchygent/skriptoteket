from __future__ import annotations

from uuid import UUID

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    RunSandboxCommand,
    RunSandboxResult,
)
from skriptoteket.application.scripting.draft_lock_checks import require_active_draft_lock
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    RunSandboxHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _sandbox_context(version_id: UUID) -> str:
    """Build sandbox session context per ADR-0038."""
    return f"sandbox:{version_id}"


class RunSandboxHandler(RunSandboxHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        session_files: SessionFileStorageProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._sessions = sessions
        self._id_generator = id_generator
        self._execute = execute
        self._session_files = session_files
        self._locks = locks
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: RunSandboxCommand,
    ) -> RunSandboxResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        now = self._clock.now()

        async with self._uow:
            version = await self._versions.get_by_id(version_id=command.version_id)
            if version is None:
                raise not_found("ToolVersion", str(command.version_id))
            if version.tool_id != command.tool_id:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="ToolVersion does not belong to the specified Tool",
                    details={
                        "tool_id": str(command.tool_id),
                        "version_id": str(command.version_id),
                        "version_tool_id": str(version.tool_id),
                    },
                )

            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=version.tool_id,
                    user_id=actor.id,
                )
                if not is_tool_maintainer:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Insufficient permissions",
                        details={"tool_id": str(version.tool_id)},
                    )
            if actor.role is Role.CONTRIBUTOR and version.created_by_user_id != actor.id:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message="Cannot run another user's draft in sandbox",
                    details={
                        "actor_user_id": str(actor.id),
                        "version_id": str(version.id),
                        "created_by_user_id": str(version.created_by_user_id),
                    },
                )

            draft_versions = await self._versions.list_for_tool(
                tool_id=version.tool_id,
                states={VersionState.DRAFT},
                limit=1,
            )
            if draft_versions:
                draft_head = draft_versions[0]
                if version.id != draft_head.id:
                    raise DomainError(
                        code=ErrorCode.CONFLICT,
                        message="Sandbox runs require the current draft head",
                        details={
                            "tool_id": str(version.tool_id),
                            "version_id": str(version.id),
                            "draft_head_id": str(draft_head.id),
                        },
                    )
                await require_active_draft_lock(
                    locks=self._locks,
                    tool_id=version.tool_id,
                    draft_head_id=draft_head.id,
                    actor=actor,
                    now=now,
                )

        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=command.tool_id,
                version_id=command.version_id,
                context=RunContext.SANDBOX,
                input_files=command.input_files,
                input_values=command.input_values,
            ),
        )

        # Persist session-scoped files for subsequent sandbox action runs (ADR-0039).
        if command.input_files:
            await self._session_files.store_files(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=_sandbox_context(command.version_id),
                files=command.input_files,
            )

        # Persist sandbox session state if run has next_actions (ADR-0038)
        state_rev: int | None = None
        run = result.run
        if run.ui_payload is not None and run.ui_payload.next_actions:
            context = _sandbox_context(command.version_id)
            async with self._uow:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=context,
                )
                # Update state (always increment state_rev on new run)
                updated_session = await self._sessions.update_state(
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=context,
                    expected_state_rev=session.state_rev,
                    state=result.normalized_state,
                )
                state_rev = updated_session.state_rev

        return RunSandboxResult(run=result.run, state_rev=state_rev)
