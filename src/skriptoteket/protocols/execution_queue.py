from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.models import ToolRunJob


class ToolRunJobClaim(BaseModel):
    model_config = ConfigDict(frozen=True)

    job: ToolRunJob
    is_adoption: bool


class ToolRunJobRepositoryProtocol(Protocol):
    async def get_by_run_id(self, *, run_id: UUID) -> ToolRunJob | None: ...

    async def create(self, *, job: ToolRunJob) -> ToolRunJob: ...

    async def update(self, *, job: ToolRunJob) -> ToolRunJob: ...

    async def claim_next(
        self,
        *,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
        queue: str = "default",
    ) -> ToolRunJobClaim | None: ...

    async def heartbeat(
        self,
        *,
        job_id: UUID,
        worker_id: str,
        now: datetime,
        lease_ttl: timedelta,
    ) -> bool: ...

    async def clear_stale_leases(
        self,
        *,
        now: datetime,
    ) -> int: ...
