from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.models import ToolRun, ToolVersion, VersionState


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

    async def create(self, *, version: ToolVersion) -> ToolVersion: ...

    async def update(self, *, version: ToolVersion) -> ToolVersion: ...


class ToolRunRepositoryProtocol(Protocol):
    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None: ...

    async def create(self, *, run: ToolRun) -> ToolRun: ...

    async def update(self, *, run: ToolRun) -> ToolRun: ...
