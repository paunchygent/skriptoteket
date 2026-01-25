from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.file_refs import build_session_file_ref
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    ToolRun,
    ToolVersion,
    VersionState,
    compute_content_hash,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.domain.scripting.tool_run_jobs import (
    ToolRunJob,
    mark_job_started,
)
from skriptoteket.domain.scripting.tool_run_jobs import (
    enqueue_job as enqueue_job_domain,
)
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.domain.scripting.ui.policy import DEFAULT_UI_POLICY, UiPolicy, UiPolicyProfileId
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerAdoptionProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
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


class FakeClock(ClockProtocol):
    def __init__(self, *, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeSleeper:
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)


class FakeIdGenerator(IdGeneratorProtocol):
    def new_uuid(self) -> UUID:
        return uuid4()


class FakeUiPolicyProvider(UiPolicyProviderProtocol):
    async def get_profile_id_for_tool(self, *, tool_id: UUID, actor: User) -> UiPolicyProfileId:
        del tool_id, actor
        return UiPolicyProfileId.DEFAULT

    async def get_profile_id_for_curated_app(
        self, *, curated_app_id: str, actor: User
    ) -> UiPolicyProfileId:
        del curated_app_id, actor
        return UiPolicyProfileId.DEFAULT

    def get_policy(self, *, profile_id: UiPolicyProfileId) -> UiPolicy:
        del profile_id
        return DEFAULT_UI_POLICY


class FakeBackendActionProvider(BackendActionProviderProtocol):
    async def list_backend_actions(
        self,
        *,
        tool_id: UUID,
        actor: User,
        policy: UiPolicy,
    ) -> list[UiFormAction]:
        del tool_id, actor, policy
        return []


class FakePromotionApplier(PromotionApplierProtocol):
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def apply_session_promotions(
        self,
        *,
        run_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        artifacts_manifest,
        promotions,
    ) -> None:
        self.calls.append(
            {
                "run_id": run_id,
                "tool_id": tool_id,
                "user_id": user_id,
                "context": context,
                "artifacts_manifest": artifacts_manifest,
                "promotions": promotions,
            }
        )


class FakeRunner(ToolRunnerProtocol):
    def __init__(self, *, result: ToolExecutionResult) -> None:
        self._result = result
        self.called = False

    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[ResolvedInputFile],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult:
        del run_id, version, context, input_files, input_values, memory_json, action_payload
        self.called = True
        return self._result


class FakeRunnerAdoption(ToolRunnerAdoptionProtocol):
    def __init__(self, *, result: ToolExecutionResult | None) -> None:
        self._result = result
        self.called = False

    async def try_adopt(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
    ) -> ToolExecutionResult | None:
        del run_id, version, context
        self.called = True
        return self._result


class _Request:
    def __init__(self, registry: dict[type[object], object]) -> None:
        self._registry = registry

    async def __aenter__(self) -> "_Request":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def get(self, key: type[object]) -> object:
        return self._registry[key]


class ContainerAdapter:
    def __init__(self, registry: dict[type[object], object]) -> None:
        self._registry = registry

    def __call__(self, *, scope: object) -> _Request:
        del scope
        return _Request(self._registry)


def make_user(*, user_id: UUID, now: datetime = DEFAULT_NOW) -> User:
    return User(
        id=user_id,
        email="worker@example.com",
        role=Role.USER,
        auth_provider=AuthProvider.LOCAL,
        external_id=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_tool_version(*, version_id: UUID, tool_id: UUID, now: datetime) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=version_id,
        tool_id=tool_id,
        version_number=1,
        state=VersionState.ACTIVE,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        created_by_user_id=uuid4(),
        created_at=now,
    )


def make_claimed_job(
    *,
    job_id: UUID,
    run_id: UUID,
    worker_id: str,
    now: datetime,
    attempts: int,
    max_attempts: int,
) -> ToolRunJob:
    base = enqueue_job_domain(
        job_id=job_id, run_id=run_id, now=now - timedelta(seconds=60)
    ).model_copy(update={"max_attempts": max_attempts})
    return mark_job_started(job=base, now=now - timedelta(seconds=60)).model_copy(
        update={
            "attempts": attempts,
            "locked_by": worker_id,
            "locked_until": now + timedelta(seconds=30),
            "updated_at": now,
        }
    )


@dataclass(slots=True)
class ClaimProcessorHarness:
    now: datetime
    worker_id: str
    actor: User
    tool_id: UUID
    version_id: UUID
    run_id: UUID
    job: ToolRunJob
    runs: InMemoryToolRunRepository
    jobs: InMemoryToolRunJobRepository
    sessions: FakeToolSessionRepository
    run_inputs: FakeRunInputStorage
    runner: FakeRunner
    runner_adoption: FakeRunnerAdoption
    promotion_applier: FakePromotionApplier
    ui_policy_provider: FakeUiPolicyProvider
    backend_actions_provider: FakeBackendActionProvider
    ui_normalizer: UiPayloadNormalizerProtocol
    clock: FakeClock
    id_generator: FakeIdGenerator
    sleeper: FakeSleeper
    container: ContainerAdapter


async def make_harness(
    *,
    now: datetime,
    worker_id: str,
    attempts: int,
    max_attempts: int,
    execute_result: ToolExecutionResult,
    adopt_result: ToolExecutionResult | None,
    input_files: list[tuple[str, bytes]] | None = None,
    session_context: str = "default",
    session_state: dict[str, JsonValue] | None = None,
    session_state_rev: int = 0,
    fail_session_update: bool = False,
) -> ClaimProcessorHarness:
    tool_id = uuid4()
    version_id = uuid4()
    actor = make_user(user_id=uuid4(), now=now)

    run_id = uuid4()
    run = start_tool_version_run(
        run_id=run_id,
        tool_id=tool_id,
        version_id=version_id,
        context=RunContext.PRODUCTION,
        requested_by_user_id=actor.id,
        session_context=session_context,
        workdir_path=str(run_id),
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now - timedelta(seconds=120),
    )
    job = make_claimed_job(
        job_id=uuid4(),
        run_id=run_id,
        worker_id=worker_id,
        now=now,
        attempts=attempts,
        max_attempts=max_attempts,
    )

    runs = InMemoryToolRunRepository()
    await runs.create(run=run)
    jobs = InMemoryToolRunJobRepository()
    await jobs.create(job=job)
    versions = InMemoryToolVersionRepository(
        versions={version_id: make_tool_version(version_id=version_id, tool_id=tool_id, now=now)}
    )
    users = InMemoryUserRepository(users={actor.id: actor})
    sessions = FakeToolSessionRepository(
        state=session_state,
        state_rev=session_state_rev,
        fail_update=fail_session_update,
    )
    uow = FakeUow()
    container = ContainerAdapter(
        {
            UnitOfWorkProtocol: uow,
            ToolRunRepositoryProtocol: runs,
            ToolRunJobRepositoryProtocol: jobs,
            ToolVersionRepositoryProtocol: versions,
            UserRepositoryProtocol: users,
            ToolSessionRepositoryProtocol: sessions,
        }
    )

    runner = FakeRunner(result=execute_result)
    runner_adoption = FakeRunnerAdoption(result=adopt_result)
    normalized_inputs: list[ResolvedInputFile] | None = None
    if input_files is not None:
        normalized_inputs = [
            ResolvedInputFile(
                name=name,
                content=content,
                ref=build_session_file_ref(name=name),
                field="documents",
            )
            for name, content in input_files
        ]

    run_inputs = FakeRunInputStorage(
        files_by_run={} if normalized_inputs is None else {run_id: normalized_inputs}
    )
    ui_policy_provider = FakeUiPolicyProvider()
    backend_actions_provider = FakeBackendActionProvider()
    promotion_applier = FakePromotionApplier()
    ui_normalizer: UiPayloadNormalizerProtocol = DeterministicUiPayloadNormalizer()
    clock = FakeClock(now=now)
    id_generator = FakeIdGenerator()
    sleeper = FakeSleeper()

    return ClaimProcessorHarness(
        now=now,
        worker_id=worker_id,
        actor=actor,
        tool_id=tool_id,
        version_id=version_id,
        run_id=run_id,
        job=job,
        runs=runs,
        jobs=jobs,
        sessions=sessions,
        run_inputs=run_inputs,
        runner=runner,
        runner_adoption=runner_adoption,
        promotion_applier=promotion_applier,
        ui_policy_provider=ui_policy_provider,
        backend_actions_provider=backend_actions_provider,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
        sleeper=sleeper,
        container=container,
    )
