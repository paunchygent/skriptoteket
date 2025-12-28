from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from skriptoteket.domain.catalog.models import ToolVersionStats

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    CreateDraftVersionResult,
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    PublishVersionCommand,
    PublishVersionResult,
    RequestChangesCommand,
    RequestChangesResult,
    RollbackVersionCommand,
    RollbackVersionResult,
    RunActiveToolCommand,
    RunActiveToolResult,
    RunSandboxCommand,
    RunSandboxResult,
    SaveDraftVersionCommand,
    SaveDraftVersionResult,
    SubmitForReviewCommand,
    SubmitForReviewResult,
)
from skriptoteket.application.scripting.interactive_sandbox import (
    StartSandboxActionCommand,
    StartSandboxActionResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunSourceKind,
    ToolRun,
    ToolVersion,
    VersionState,
)


class ToolVersionRepositoryProtocol(Protocol):
    async def get_by_id(self, *, version_id: UUID) -> ToolVersion | None: ...

    async def get_active_for_tool(self, *, tool_id: UUID) -> ToolVersion | None: ...

    async def get_latest_for_tool(self, *, tool_id: UUID) -> ToolVersion | None: ...

    async def list_for_tool(
        self,
        *,
        tool_id: UUID,
        states: set[VersionState] | None = None,
        limit: int = 50,
    ) -> list[ToolVersion]: ...

    async def get_next_version_number(self, *, tool_id: UUID) -> int: ...

    async def get_version_stats_for_tools(
        self, *, tool_ids: list[UUID]
    ) -> dict[UUID, ToolVersionStats]:
        """Get version statistics for multiple tools in one batch query (ADR-0033)."""
        ...

    async def create(self, *, version: ToolVersion) -> ToolVersion: ...

    async def update(self, *, version: ToolVersion) -> ToolVersion: ...


class ToolRunRepositoryProtocol(Protocol):
    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None: ...

    async def create(self, *, run: ToolRun) -> ToolRun: ...

    async def update(self, *, run: ToolRun) -> ToolRun: ...

    async def get_latest_for_user_and_tool(
        self,
        *,
        user_id: UUID,
        tool_id: UUID,
        context: RunContext,
    ) -> ToolRun | None: ...

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        context: RunContext,
        limit: int = 50,
    ) -> list[ToolRun]: ...

    async def count_for_user_this_month(
        self,
        *,
        user_id: UUID,
        context: RunContext,
    ) -> int: ...

    async def list_recent_tools_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 10,
    ) -> list["RecentRunRow"]: ...


class RecentRunRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_kind: RunSourceKind
    tool_id: UUID
    curated_app_id: str | None = None
    last_used_at: datetime


class ExecuteToolVersionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult: ...


class CreateDraftVersionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: CreateDraftVersionCommand,
    ) -> CreateDraftVersionResult: ...


class SaveDraftVersionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: SaveDraftVersionCommand,
    ) -> SaveDraftVersionResult: ...


class SubmitForReviewHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: SubmitForReviewCommand,
    ) -> SubmitForReviewResult: ...


class PublishVersionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: PublishVersionCommand,
    ) -> PublishVersionResult: ...


class RollbackVersionHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RollbackVersionCommand,
    ) -> RollbackVersionResult: ...


class RequestChangesHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RequestChangesCommand,
    ) -> RequestChangesResult: ...


class RunSandboxHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: RunSandboxCommand,
    ) -> RunSandboxResult: ...


class RunActiveToolHandlerProtocol(Protocol):
    """Protocol for user-facing execution of published tools."""

    async def handle(
        self,
        *,
        actor: User,
        command: RunActiveToolCommand,
    ) -> RunActiveToolResult: ...


class StartSandboxActionHandlerProtocol(Protocol):
    """Protocol for starting sandbox actions (ADR-0038)."""

    async def handle(
        self,
        *,
        actor: User,
        command: StartSandboxActionCommand,
    ) -> StartSandboxActionResult: ...
