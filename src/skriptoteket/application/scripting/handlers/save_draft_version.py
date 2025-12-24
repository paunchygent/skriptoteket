from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    SaveDraftVersionCommand,
    SaveDraftVersionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import VersionState, save_draft_snapshot
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    SaveDraftVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SaveDraftVersionHandler(SaveDraftVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: SaveDraftVersionCommand,
    ) -> SaveDraftVersionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        now = self._clock.now()

        async with self._uow:
            previous = await self._versions.get_by_id(version_id=command.version_id)
            if previous is None:
                raise not_found("ToolVersion", str(command.version_id))

            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=previous.tool_id,
                    user_id=actor.id,
                )
                if not is_tool_maintainer:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Insufficient permissions",
                        details={"tool_id": str(previous.tool_id)},
                    )

            if actor.role is Role.CONTRIBUTOR and previous.created_by_user_id != actor.id:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message="Cannot edit another user's draft",
                    details={
                        "actor_user_id": str(actor.id),
                        "version_id": str(previous.id),
                        "created_by_user_id": str(previous.created_by_user_id),
                    },
                )

            if command.expected_parent_version_id != previous.id:
                raise validation_error(
                    "expected_parent_version_id must match version_id",
                    details={
                        "version_id": str(previous.id),
                        "expected_parent_version_id": str(command.expected_parent_version_id),
                    },
                )

            draft_versions = await self._versions.list_for_tool(
                tool_id=previous.tool_id,
                states={VersionState.DRAFT},
                limit=1,
            )
            if not draft_versions:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Tool has no draft version to save",
                    details={"tool_id": str(previous.tool_id)},
                )

            draft_head = draft_versions[0]
            if draft_head.id != command.expected_parent_version_id:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Draft head has advanced; reload before saving",
                    details={
                        "tool_id": str(previous.tool_id),
                        "expected_parent_version_id": str(command.expected_parent_version_id),
                        "current_head_version_id": str(draft_head.id),
                    },
                )

            new_version_number = await self._versions.get_next_version_number(
                tool_id=previous.tool_id
            )
            effective_settings_schema = (
                command.settings_schema
                if "settings_schema" in command.model_fields_set
                else previous.settings_schema
            )
            effective_usage_instructions = (
                command.usage_instructions
                if "usage_instructions" in command.model_fields_set
                else previous.usage_instructions
            )
            saved = save_draft_snapshot(
                previous_version=previous,
                new_version_id=self._id_generator.new_uuid(),
                new_version_number=new_version_number,
                source_code=command.source_code,
                entrypoint=command.entrypoint,
                settings_schema=effective_settings_schema,
                usage_instructions=effective_usage_instructions,
                saved_by_user_id=actor.id,
                change_summary=command.change_summary,
                now=now,
            )
            created = await self._versions.create(version=saved)

        return SaveDraftVersionResult(version=created)
