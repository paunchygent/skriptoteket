from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.file_refs import build_session_file_ref
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
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
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import UiPayloadNormalizerProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.workers.execution_queue_repository_fakes import (
    DEFAULT_NOW,
    FakeRunInputStorage,
    FakeToolSessionRepository,
    FakeUow,
    InMemoryToolRunJobRepository,
    InMemoryToolRunRepository,
    InMemoryToolVersionRepository,
    InMemoryUserRepository,
)
from tests.unit.workers.execution_queue_runtime_fakes import (
    FakeBackendActionProvider,
    FakeClock,
    FakeIdGenerator,
    FakePromotionApplier,
    FakeRunner,
    FakeRunnerAdoption,
    FakeSleeper,
    FakeUiPolicyProvider,
)


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
        content_hash=compute_content_hash(
            entrypoint=entrypoint,
            source_code=source_code,
            bundle_files={},
        ),
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
