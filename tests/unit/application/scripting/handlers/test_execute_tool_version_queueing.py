from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    ToolVersionOverride,
)
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    ExecuteToolVersionHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.input_files import InputManifest
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolVersion,
    VersionState,
    compute_content_hash,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.domain.scripting.tool_inputs import ToolInputFileField
from skriptoteket.domain.scripting.ui.normalizer import DeterministicUiPayloadNormalizer
from skriptoteket.domain.scripting.ui.policy import DEFAULT_UI_POLICY, UiPolicyProfileId
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:  # noqa: D401
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


def _make_tool_version(*, tool_id: UUID, now: datetime) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=uuid4(),
        tool_id=tool_id,
        version_number=1,
        state=VersionState.ACTIVE,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        created_by_user_id=uuid4(),
        created_at=now,
        input_schema=[ToolInputFileField(name="files", label="Files", min=0, max=10)],
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_queue_enabled_production_enqueues_and_does_not_call_runner(
    now: datetime,
) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()

    version = _make_tool_version(tool_id=tool_id, now=now).model_copy(
        update={"input_schema": [ToolInputFileField(name="files", label="Files", min=1, max=10)]}
    )

    uow = FakeUow()
    settings = Mock(spec=Settings)
    settings.RUNNER_QUEUE_ENABLED = True
    settings.RUNNER_QUEUE_MAX_ATTEMPTS = 3

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    jobs = AsyncMock(spec=ToolRunJobRepositoryProtocol)
    run_inputs = AsyncMock(spec=RunInputStorageProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    runner = AsyncMock(spec=ToolRunnerProtocol)
    file_refs = AsyncMock(spec=FileRefResolverProtocol)
    file_refs.resolve_refs.return_value = []
    promotion_applier = AsyncMock(spec=PromotionApplierProtocol)

    ui_policy_provider = Mock(spec=UiPolicyProviderProtocol)
    ui_policy_provider.get_profile_id_for_tool = AsyncMock(return_value=UiPolicyProfileId.DEFAULT)
    ui_policy_provider.get_policy.return_value = DEFAULT_UI_POLICY

    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    backend_actions.list_backend_actions.return_value = []

    ui_normalizer = DeterministicUiPayloadNormalizer()

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [run_id, job_id]

    handler = ExecuteToolVersionHandler(
        uow=uow,
        settings=settings,
        versions=versions,
        runs=runs,
        jobs=jobs,
        run_inputs=run_inputs,
        sessions=sessions,
        runner=runner,
        file_refs=file_refs,
        promotion_applier=promotion_applier,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=ExecuteToolVersionCommand(
            tool_id=tool_id,
            version_id=version.id,
            context=RunContext.PRODUCTION,
            session_context="default",
            input_files=[("input.txt", b"input")],
        ),
    )

    assert result.run.status is RunStatus.QUEUED
    assert result.run.started_at is None
    assert result.state_update.kind == "no_change"

    runs.create.assert_awaited_once()
    jobs.create.assert_awaited_once()
    run_inputs.store.assert_awaited_once()
    runner.execute.assert_not_awaited()

    created_run = runs.create.call_args.kwargs["run"]
    assert created_run.session_context == "default"

    stored_call = run_inputs.store.call_args.kwargs
    assert stored_call["run_id"] == run_id
    stored_files = stored_call["files"]
    assert len(stored_files) == 1
    stored_file = stored_files[0]
    assert isinstance(stored_file, ResolvedInputFile)
    assert stored_file.name == "input.txt"
    assert stored_file.content == b"input"
    assert stored_file.ref == "session:input.txt"

    created_job = jobs.create.call_args.kwargs["job"]
    assert created_job.run_id == run_id
    assert created_job.status is RunStatus.QUEUED
    assert created_job.attempts == 0
    assert created_job.max_attempts == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_queue_enabled_without_files_does_not_store_inputs(
    now: datetime,
) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    run_id = uuid4()
    job_id = uuid4()

    version = _make_tool_version(tool_id=tool_id, now=now)

    uow = FakeUow()
    settings = Mock(spec=Settings)
    settings.RUNNER_QUEUE_ENABLED = True
    settings.RUNNER_QUEUE_MAX_ATTEMPTS = 1

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    jobs = AsyncMock(spec=ToolRunJobRepositoryProtocol)
    run_inputs = AsyncMock(spec=RunInputStorageProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    runner = AsyncMock(spec=ToolRunnerProtocol)
    file_refs = AsyncMock(spec=FileRefResolverProtocol)
    file_refs.resolve_refs.return_value = []
    promotion_applier = AsyncMock(spec=PromotionApplierProtocol)

    ui_policy_provider = Mock(spec=UiPolicyProviderProtocol)
    ui_policy_provider.get_profile_id_for_tool = AsyncMock(return_value=UiPolicyProfileId.DEFAULT)
    ui_policy_provider.get_policy.return_value = DEFAULT_UI_POLICY

    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    backend_actions.list_backend_actions.return_value = []

    ui_normalizer = DeterministicUiPayloadNormalizer()

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [run_id, job_id]

    handler = ExecuteToolVersionHandler(
        uow=uow,
        settings=settings,
        versions=versions,
        runs=runs,
        jobs=jobs,
        run_inputs=run_inputs,
        sessions=sessions,
        runner=runner,
        file_refs=file_refs,
        promotion_applier=promotion_applier,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=ExecuteToolVersionCommand(
            tool_id=tool_id,
            version_id=version.id,
            context=RunContext.PRODUCTION,
            session_context="default",
        ),
    )

    assert result.run.status is RunStatus.QUEUED
    run_inputs.store.assert_not_awaited()
    runner.execute.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "command",
    [
        ExecuteToolVersionCommand(
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.SANDBOX,
            session_context="default",
        ),
        ExecuteToolVersionCommand(
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.PRODUCTION,
            session_context="default",
            action_payload={"action_id": "step", "input": {}, "state": {}},
        ),
        ExecuteToolVersionCommand(
            tool_id=uuid4(),
            version_id=uuid4(),
            context=RunContext.PRODUCTION,
            session_context="default",
            version_override=ToolVersionOverride(source_code="print('x')"),
        ),
    ],
)
async def test_execute_tool_version_when_not_queueable_does_not_enqueue(
    now: datetime,
    command: ExecuteToolVersionCommand,
    monkeypatch,
) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = command.tool_id

    version = _make_tool_version(tool_id=tool_id, now=now).model_copy(
        update={"id": command.version_id}
    )

    uow = FakeUow()
    settings = Mock(spec=Settings)
    settings.RUNNER_QUEUE_ENABLED = True
    settings.RUNNER_QUEUE_MAX_ATTEMPTS = 1

    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = version

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    jobs = AsyncMock(spec=ToolRunJobRepositoryProtocol)
    run_inputs = AsyncMock(spec=RunInputStorageProtocol)
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    runner = AsyncMock(spec=ToolRunnerProtocol)
    file_refs = AsyncMock(spec=FileRefResolverProtocol)
    file_refs.resolve_refs.return_value = []
    promotion_applier = AsyncMock(spec=PromotionApplierProtocol)

    ui_policy_provider = Mock(spec=UiPolicyProviderProtocol)
    ui_policy_provider.get_profile_id_for_tool = AsyncMock(return_value=UiPolicyProfileId.DEFAULT)
    ui_policy_provider.get_policy.return_value = DEFAULT_UI_POLICY

    backend_actions = AsyncMock(spec=BackendActionProviderProtocol)
    backend_actions.list_backend_actions.return_value = []

    ui_normalizer = DeterministicUiPayloadNormalizer()

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    dummy_run = start_tool_version_run(
        run_id=uuid4(),
        tool_id=tool_id,
        version_id=version.id,
        context=command.context,
        requested_by_user_id=actor.id,
        session_context=command.session_context,
        workdir_path="/tmp/run",
        input_filename=None,
        input_size_bytes=0,
        input_manifest=InputManifest(),
        now=now,
    )
    dummy_pipeline_result = ExecuteToolVersionResult(run=dummy_run)
    pipeline = AsyncMock(return_value=dummy_pipeline_result)

    import skriptoteket.application.scripting.handlers.execute_tool_version as handler_module

    monkeypatch.setattr(handler_module, "execute_tool_version_pipeline", pipeline)

    handler = ExecuteToolVersionHandler(
        uow=uow,
        settings=settings,
        versions=versions,
        runs=runs,
        jobs=jobs,
        run_inputs=run_inputs,
        sessions=sessions,
        runner=runner,
        file_refs=file_refs,
        promotion_applier=promotion_applier,
        ui_policy_provider=ui_policy_provider,
        backend_actions=backend_actions,
        ui_normalizer=ui_normalizer,
        clock=clock,
        id_generator=id_generator,
    )

    await handler.handle(actor=actor, command=command.model_copy(update={"tool_id": tool_id}))

    jobs.create.assert_not_awaited()
    run_inputs.store.assert_not_awaited()
    pipeline.assert_awaited_once()
