"""Start sandbox action handler (ADR-0038).

Similar to start_action.py but for sandbox context with version-specific execution.
"""

from __future__ import annotations

import json
from uuid import UUID

from skriptoteket.application.scripting.commands import ExecuteToolVersionCommand
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
    StartSandboxActionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import RunContext
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    StartSandboxActionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _sandbox_context(version_id: UUID) -> str:
    """Build sandbox session context per ADR-0038."""
    return f"sandbox:{version_id}"


class StartSandboxActionHandler(StartSandboxActionHandlerProtocol):
    """Start an interactive sandbox action (ADR-0038).

    The tool receives JSON input bytes with the shape:
    {"action_id": str, "input": {...}, "state": {...}}.
    """

    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._sessions = sessions
        self._execute = execute

    async def handle(
        self,
        *,
        actor: User,
        command: StartSandboxActionCommand,
    ) -> StartSandboxActionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        context = _sandbox_context(command.version_id)

        # Validate version and permissions
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
                    },
                )

            # Contributor permission checks
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
                if version.created_by_user_id != actor.id:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Cannot run another user's draft in sandbox",
                        details={
                            "actor_user_id": str(actor.id),
                            "version_id": str(version.id),
                        },
                    )

            # Get session and validate state_rev
            session = await self._sessions.get(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )
            if session is None:
                raise DomainError(
                    code=ErrorCode.NOT_FOUND,
                    message="Sandbox session not found. Run the tool first.",
                    details={"version_id": str(command.version_id)},
                )
            if session.state_rev != command.expected_state_rev:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Session state_rev conflict",
                    details={
                        "expected_state_rev": command.expected_state_rev,
                        "current_state_rev": session.state_rev,
                    },
                )

            current_state = session.state

        # Build action.json payload
        payload = {
            "action_id": command.action_id,
            "input": command.input,
            "state": current_state,
        }
        input_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # Execute the tool version in sandbox context
        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=command.tool_id,
                version_id=command.version_id,
                context=RunContext.SANDBOX,
                input_files=[("action.json", input_bytes)],
            ),
        )

        # Update session with new state
        async with self._uow:
            updated_session = await self._sessions.update_state(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
                expected_state_rev=command.expected_state_rev,
                state=result.normalized_state,
            )

        return StartSandboxActionResult(
            run_id=result.run.id,
            state_rev=updated_session.state_rev,
        )
