from __future__ import annotations

from skriptoteket.application.scripting.draft_lock_checks import require_active_draft_lock
from skriptoteket.application.scripting.tool_settings import (
    SaveSandboxSettingsCommand,
    SaveSandboxSettingsResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import VersionState
from skriptoteket.domain.scripting.tool_sessions import validate_expected_state_rev
from skriptoteket.domain.scripting.tool_settings import normalize_tool_settings_schema
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_settings import (
    SaveSandboxSettingsHandlerProtocol,
    ToolSettingsServiceProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SaveSandboxSettingsHandler(SaveSandboxSettingsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        settings_service: ToolSettingsServiceProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._locks = locks
        self._clock = clock
        self._settings_service = settings_service

    async def handle(
        self,
        *,
        actor: User,
        command: SaveSandboxSettingsCommand,
    ) -> SaveSandboxSettingsResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        validate_expected_state_rev(expected_state_rev=command.expected_state_rev)

        settings_schema = normalize_tool_settings_schema(
            settings_schema=command.settings_schema,
        )
        if settings_schema is None:
            raise validation_error("settings_schema is required")

        now = self._clock.now()

        async with self._uow:
            version = await self._versions.get_by_id(version_id=command.version_id)
            if version is None:
                raise not_found("ToolVersion", str(command.version_id))

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
                        message="Cannot edit another user's draft settings",
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
                        message="Sandbox settings require the current draft head",
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

            settings_state = await self._settings_service.save_sandbox_settings(
                tool_id=version.tool_id,
                user_id=actor.id,
                draft_head_id=version.id,
                settings_schema=settings_schema,
                expected_state_rev=command.expected_state_rev,
                values=command.values,
            )

        return SaveSandboxSettingsResult(settings=settings_state)
