from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import ToolRun, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.domain.scripting.tool_run_jobs import ToolRunJob
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

DEFAULT_NOW = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class InMemoryToolRunRepository:
    def __init__(self) -> None:
        self._runs: dict[UUID, ToolRun] = {}

    async def get_by_id(self, *, run_id: UUID) -> ToolRun | None:
        return self._runs.get(run_id)

    async def create(self, *, run: ToolRun) -> ToolRun:
        self._runs[run.id] = run
        return run

    async def update(self, *, run: ToolRun) -> ToolRun:
        self._runs[run.id] = run
        return run


class InMemoryToolRunJobRepository(ToolRunJobRepositoryProtocol):
    def __init__(self) -> None:
        self._jobs_by_run: dict[UUID, ToolRunJob] = {}

    async def get_by_run_id(self, *, run_id: UUID) -> ToolRunJob | None:
        return self._jobs_by_run.get(run_id)

    async def create(self, *, job: ToolRunJob) -> ToolRunJob:
        self._jobs_by_run[job.run_id] = job
        return job

    async def update(self, *, job: ToolRunJob) -> ToolRunJob:
        self._jobs_by_run[job.run_id] = job
        return job

    async def claim_next(
        self, *, worker_id: str, now: datetime, lease_ttl: timedelta, queue: str = "default"
    ):
        raise NotImplementedError

    async def heartbeat(
        self, *, job_id: UUID, worker_id: str, now: datetime, lease_ttl: timedelta
    ) -> bool:
        for existing in self._jobs_by_run.values():
            if existing.id != job_id:
                continue
            if existing.locked_by != worker_id:
                return False
            await self.update(
                job=existing.model_copy(update={"locked_until": now + lease_ttl, "updated_at": now})
            )
            return True
        return False

    async def clear_stale_leases(self, *, now: datetime) -> int:
        raise NotImplementedError


class InMemoryToolVersionRepository:
    def __init__(self, *, versions: dict[UUID, ToolVersion]) -> None:
        self._versions = versions

    async def get_by_id(self, *, version_id: UUID) -> ToolVersion | None:
        return self._versions.get(version_id)


class InMemoryUserRepository:
    def __init__(self, *, users: dict[UUID, User]) -> None:
        self._users = users

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._users.get(user_id)


class FakeToolSessionRepository:
    def __init__(
        self,
        *,
        state: dict[str, JsonValue] | None = None,
        state_rev: int = 0,
        fail_update: bool = False,
    ) -> None:
        self._session: ToolSession | None = None
        self._state = {} if state is None else state
        self._state_rev = state_rev
        self._fail_update = fail_update
        self.update_calls: list[dict[str, object]] = []

    async def get_or_create(
        self,
        *,
        session_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> ToolSession:
        if self._session is None:
            self._session = ToolSession(
                id=session_id,
                tool_id=tool_id,
                user_id=user_id,
                context=context,
                state=self._state,
                state_rev=self._state_rev,
                created_at=DEFAULT_NOW,
                updated_at=DEFAULT_NOW,
            )
        return self._session

    async def update_state(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        expected_state_rev: int,
        state: dict[str, JsonValue],
    ) -> ToolSession:
        self.update_calls.append(
            {
                "tool_id": tool_id,
                "user_id": user_id,
                "context": context,
                "expected_state_rev": expected_state_rev,
                "state": state,
            }
        )
        if self._fail_update:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Failed to persist state",
            )
        session_id = self._session.id if self._session else uuid4()
        created_at = self._session.created_at if self._session else DEFAULT_NOW
        self._session = ToolSession(
            id=session_id,
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            state=state,
            state_rev=expected_state_rev + 1,
            created_at=created_at,
            updated_at=DEFAULT_NOW,
        )
        return self._session


class FakeRunInputStorage(RunInputStorageProtocol):
    def __init__(self, *, files_by_run: dict[UUID, list[ResolvedInputFile]] | None = None) -> None:
        self._files_by_run = files_by_run or {}
        self.deleted: list[UUID] = []

    async def store(self, *, run_id: UUID, files: list[ResolvedInputFile]) -> None:
        self._files_by_run[run_id] = files

    async def get(self, *, run_id: UUID) -> list[ResolvedInputFile]:
        return self._files_by_run.get(run_id, [])

    async def delete(self, *, run_id: UUID) -> None:
        self.deleted.append(run_id)
        self._files_by_run.pop(run_id, None)
