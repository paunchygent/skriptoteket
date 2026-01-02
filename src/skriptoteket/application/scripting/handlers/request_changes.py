from __future__ import annotations

from skriptoteket.application.scripting.commands import (
    RequestChangesCommand,
    RequestChangesResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import VersionState, create_draft_version
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.scripting import (
    RequestChangesHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class RequestChangesHandler(RequestChangesHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: RequestChangesCommand,
    ) -> RequestChangesResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        now = self._clock.now()

        async with self._uow:
            reviewed_version = await self._versions.get_by_id(version_id=command.version_id)
            if reviewed_version is None:
                raise not_found("ToolVersion", str(command.version_id))
            if reviewed_version.state is not VersionState.IN_REVIEW:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Only in_review versions can be requested changes",
                    details={"state": reviewed_version.state.value},
                )

            archived_in_review = reviewed_version.model_copy(
                update={
                    "state": VersionState.ARCHIVED,
                    "reviewed_by_user_id": actor.id,
                    "reviewed_at": now,
                }
            )
            archived_persisted = await self._versions.update(version=archived_in_review)

            new_version_number = await self._versions.get_next_version_number(
                tool_id=reviewed_version.tool_id
            )
            draft = create_draft_version(
                version_id=self._id_generator.new_uuid(),
                tool_id=reviewed_version.tool_id,
                version_number=new_version_number,
                source_code=reviewed_version.source_code,
                entrypoint=reviewed_version.entrypoint,
                settings_schema=reviewed_version.settings_schema,
                input_schema=reviewed_version.input_schema,
                created_by_user_id=reviewed_version.created_by_user_id,
                derived_from_version_id=reviewed_version.id,
                change_summary=command.message,
                now=now,
            )
            draft_persisted = await self._versions.create(version=draft)

        return RequestChangesResult(
            new_draft_version=draft_persisted,
            archived_in_review_version=archived_persisted,
        )
