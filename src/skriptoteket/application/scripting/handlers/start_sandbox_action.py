"""Start sandbox action handler (ADR-0038).

Similar to start_action.py but for sandbox context with version-specific execution.
"""

from __future__ import annotations

import json
from uuid import UUID

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.draft_lock_checks import require_active_draft_lock
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
    StartSandboxActionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import RunContext, VersionState
from skriptoteket.domain.scripting.sandbox_snapshots import SandboxSnapshot
from skriptoteket.domain.scripting.tool_settings import compute_sandbox_settings_context
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    StartSandboxActionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _sandbox_context(snapshot_id: UUID) -> str:
    """Build sandbox session context per ADR-0044."""
    return f"sandbox:{snapshot_id}"


def _ensure_snapshot_is_valid(
    *,
    snapshot: SandboxSnapshot,
    command: StartSandboxActionCommand,
) -> None:
    if snapshot.tool_id != command.tool_id:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Sandbox snapshot does not belong to the specified Tool",
            details={
                "tool_id": str(command.tool_id),
                "snapshot_id": str(snapshot.id),
                "snapshot_tool_id": str(snapshot.tool_id),
            },
        )
    if snapshot.draft_head_id != command.version_id:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Sandbox snapshot does not match the specified draft head",
            details={
                "version_id": str(command.version_id),
                "snapshot_id": str(snapshot.id),
                "snapshot_draft_head_id": str(snapshot.draft_head_id),
            },
        )


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
        session_files: SessionFileStorageProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        snapshots: SandboxSnapshotRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._sessions = sessions
        self._execute = execute
        self._session_files = session_files
        self._locks = locks
        self._clock = clock
        self._snapshots = snapshots

    async def handle(
        self,
        *,
        actor: User,
        command: StartSandboxActionCommand,
    ) -> StartSandboxActionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        now = self._clock.now()
        context = _sandbox_context(command.snapshot_id)

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
                        message="Sandbox actions require the current draft head",
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

            snapshot = await self._snapshots.get_by_id(snapshot_id=command.snapshot_id)
            if snapshot is None:
                raise not_found("SandboxSnapshot", str(command.snapshot_id))
            if snapshot.expires_at <= now:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Sandbox snapshot has expired. Run the sandbox again.",
                    details={"snapshot_id": str(command.snapshot_id)},
                )
            _ensure_snapshot_is_valid(snapshot=snapshot, command=command)

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
                    details={
                        "version_id": str(command.version_id),
                        "snapshot_id": str(command.snapshot_id),
                    },
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

        persisted_files = await self._session_files.get_files(
            tool_id=command.tool_id,
            user_id=actor.id,
            context=context,
        )

        settings_context: str | None = None
        if snapshot.settings_schema is not None:
            settings_context = compute_sandbox_settings_context(
                draft_head_id=snapshot.draft_head_id,
                settings_schema=snapshot.settings_schema,
            )

        # Execute the tool version in sandbox context
        result = await self._execute.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=command.tool_id,
                version_id=command.version_id,
                snapshot_id=command.snapshot_id,
                context=RunContext.SANDBOX,
                settings_context=settings_context,
                version_override=ToolVersionOverride(
                    entrypoint=snapshot.entrypoint,
                    source_code=snapshot.source_code,
                    settings_schema=snapshot.settings_schema,
                    input_schema=snapshot.input_schema,
                    usage_instructions=snapshot.usage_instructions,
                ),
                input_files=[*persisted_files, ("action.json", input_bytes)],
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
