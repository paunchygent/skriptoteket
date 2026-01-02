from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    CreateDraftVersionResult,
)
from skriptoteket.application.scripting.draft_lock_checks import require_active_draft_lock
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import VersionState, create_draft_version
from skriptoteket.domain.scripting.policies import require_can_view_version
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class CreateDraftVersionHandler(CreateDraftVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._maintainers = maintainers
        self._versions = versions
        self._locks = locks
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: CreateDraftVersionCommand,
    ) -> CreateDraftVersionResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        now = self._clock.now()

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            is_tool_maintainer = actor.role in {Role.ADMIN, Role.SUPERUSER}
            if actor.role is Role.CONTRIBUTOR:
                is_tool_maintainer = await self._maintainers.is_maintainer(
                    tool_id=tool.id,
                    user_id=actor.id,
                )
                if not is_tool_maintainer:
                    raise DomainError(
                        code=ErrorCode.FORBIDDEN,
                        message="Insufficient permissions",
                        details={"tool_id": str(tool.id)},
                    )

            if command.derived_from_version_id is not None:
                derived_from = await self._versions.get_by_id(
                    version_id=command.derived_from_version_id
                )
                if derived_from is None:
                    raise not_found("ToolVersion", str(command.derived_from_version_id))
                if derived_from.tool_id != tool.id:
                    raise DomainError(
                        code=ErrorCode.CONFLICT,
                        message="derived_from_version_id does not belong to the specified Tool",
                        details={
                            "tool_id": str(tool.id),
                            "derived_from_version_id": str(command.derived_from_version_id),
                            "derived_from_tool_id": str(derived_from.tool_id),
                        },
                    )
                if actor.role is Role.CONTRIBUTOR:
                    require_can_view_version(
                        actor=actor,
                        version=derived_from,
                        is_tool_maintainer=is_tool_maintainer,
                    )
            else:
                derived_from = None

            draft_versions = await self._versions.list_for_tool(
                tool_id=tool.id,
                states={VersionState.DRAFT},
                limit=1,
            )
            if draft_versions:
                draft_head = draft_versions[0]
                await require_active_draft_lock(
                    locks=self._locks,
                    tool_id=tool.id,
                    draft_head_id=draft_head.id,
                    actor=actor,
                    now=now,
                )

            version_number = await self._versions.get_next_version_number(tool_id=tool.id)
            effective_settings_schema = (
                command.settings_schema
                if "settings_schema" in command.model_fields_set
                else (derived_from.settings_schema if derived_from is not None else None)
            )
            effective_input_schema = (
                command.input_schema
                if "input_schema" in command.model_fields_set
                else (derived_from.input_schema if derived_from is not None else [])
            )
            effective_usage_instructions = (
                command.usage_instructions
                if "usage_instructions" in command.model_fields_set
                else (derived_from.usage_instructions if derived_from is not None else None)
            )
            draft = create_draft_version(
                version_id=self._id_generator.new_uuid(),
                tool_id=tool.id,
                version_number=version_number,
                source_code=command.source_code,
                entrypoint=command.entrypoint,
                settings_schema=effective_settings_schema,
                input_schema=effective_input_schema,
                usage_instructions=effective_usage_instructions,
                created_by_user_id=actor.id,
                derived_from_version_id=command.derived_from_version_id,
                change_summary=command.change_summary,
                now=now,
            )
            created = await self._versions.create(version=draft)

        return CreateDraftVersionResult(version=created)
