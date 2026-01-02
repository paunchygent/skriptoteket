from __future__ import annotations

from uuid import UUID

from skriptoteket.application.scripting.session_files import (
    ListSandboxSessionFilesQuery,
    ListSandboxSessionFilesResult,
    SessionFileInfo,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ListSandboxSessionFilesHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _sandbox_context(snapshot_id: UUID) -> str:
    """Build sandbox session context per ADR-0044."""
    return f"sandbox:{snapshot_id}"


def _ensure_snapshot_matches_version(*, snapshot, version) -> None:
    if snapshot.tool_id != version.tool_id:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Sandbox snapshot does not belong to the specified Tool",
            details={
                "tool_id": str(version.tool_id),
                "snapshot_id": str(snapshot.id),
                "snapshot_tool_id": str(snapshot.tool_id),
            },
        )
    if snapshot.draft_head_id != version.id:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message="Sandbox snapshot does not match the specified draft head",
            details={
                "version_id": str(version.id),
                "snapshot_id": str(snapshot.id),
                "snapshot_draft_head_id": str(snapshot.draft_head_id),
            },
        )


class ListSandboxSessionFilesHandler(ListSandboxSessionFilesHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        snapshots: SandboxSnapshotRepositoryProtocol,
        session_files: SessionFileStorageProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._maintainers = maintainers
        self._snapshots = snapshots
        self._session_files = session_files
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        query: ListSandboxSessionFilesQuery,
    ) -> ListSandboxSessionFilesResult:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)
        now = self._clock.now()

        async with self._uow:
            version = await self._versions.get_by_id(version_id=query.version_id)
            if version is None:
                raise not_found("ToolVersion", str(query.version_id))

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
                        message="Cannot access another user's draft in sandbox",
                        details={
                            "actor_user_id": str(actor.id),
                            "version_id": str(version.id),
                        },
                    )

            snapshot = await self._snapshots.get_by_id(snapshot_id=query.snapshot_id)
            if snapshot is None:
                raise not_found("SandboxSnapshot", str(query.snapshot_id))
            if snapshot.expires_at <= now:
                raise DomainError(
                    code=ErrorCode.CONFLICT,
                    message="Sandbox snapshot has expired. Run the sandbox again.",
                    details={"snapshot_id": str(query.snapshot_id)},
                )
            _ensure_snapshot_matches_version(snapshot=snapshot, version=version)

        files = await self._session_files.list_files(
            tool_id=version.tool_id,
            user_id=actor.id,
            context=_sandbox_context(query.snapshot_id),
        )

        return ListSandboxSessionFilesResult(
            tool_id=version.tool_id,
            version_id=query.version_id,
            snapshot_id=query.snapshot_id,
            files=[SessionFileInfo(name=item.name, bytes=item.bytes) for item in files],
        )
