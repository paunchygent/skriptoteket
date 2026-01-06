from __future__ import annotations

from skriptoteket.application.catalog.publish_requirements import (
    ensure_tool_publish_requirements,
)
from skriptoteket.application.scripting.commands import (
    SubmitForReviewCommand,
    SubmitForReviewResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.models import submit_for_review
from skriptoteket.protocols.catalog import (
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.scripting import (
    SubmitForReviewHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class SubmitForReviewHandler(SubmitForReviewHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._versions = versions
        self._maintainers = maintainers
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: SubmitForReviewCommand,
    ) -> SubmitForReviewResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

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

            if actor.role is Role.CONTRIBUTOR and version.created_by_user_id != actor.id:
                raise DomainError(
                    code=ErrorCode.FORBIDDEN,
                    message="Cannot submit another user's draft for review",
                    details={
                        "actor_user_id": str(actor.id),
                        "version_id": str(version.id),
                        "created_by_user_id": str(version.created_by_user_id),
                    },
                )

            tool = await self._tools.get_by_id(tool_id=version.tool_id)
            if tool is None:
                raise not_found("Tool", str(version.tool_id))

            await ensure_tool_publish_requirements(
                tool=tool,
                list_tag_ids=self._tools.list_tag_ids,
            )

            submitted = submit_for_review(
                version=version,
                submitted_by_user_id=actor.id,
                review_note=command.review_note,
                now=now,
            )
            updated = await self._versions.update(version=submitted)

        return SubmitForReviewResult(version=updated)
