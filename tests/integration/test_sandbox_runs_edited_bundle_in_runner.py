"""A sandbox run of gruppgenerator executes the unsaved roster.py edit in the real runner."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
    RunSandboxCommand,
    SandboxSnapshotPayload,
)
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    _apply_version_override,
)
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.domain.scripting.ui.state_update import NoChangeStateUpdate
from skriptoteket.infrastructure.runner.artifact_manager import FilesystemArtifactManager
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.docker.contract_selection import (
    RunnerContract,
    StaticRunnerContractSelector,
)
from skriptoteket.infrastructure.runner.docker.request_factory import V3RunnerRequestFactory
from skriptoteket.infrastructure.runner.docker.result_parser import V3RunnerResultParser
from skriptoteket.infrastructure.runner.docker_runner import DockerRunnerLimits, DockerToolRunner
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.gruppgenerator_bundle_support import (
    EDIT_MARKER,
    edited_roster_py,
    gruppgenerator_draft,
    gruppgenerator_files,
)
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_settings_mock,
    make_tool_run,
    make_tool_session,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker]

ROSTER_CSV = "Namn,Klass\nAnna Berg,7A\nBo Ek,7A\nCia Lund,7A\n".encode()


class _RealRunnerExecute:
    """Applies the sandbox override to the draft and runs it in the real runner container."""

    def __init__(self, *, draft: ToolVersion, runner: DockerToolRunner) -> None:
        self._draft = draft
        self._runner = runner
        self.result: ToolExecutionResult | None = None

    async def handle(
        self, *, actor: User, command: ExecuteToolVersionCommand
    ) -> ExecuteToolVersionResult:
        assert command.version_override is not None
        version = _apply_version_override(version=self._draft, override=command.version_override)
        self.result = await self._runner.execute(
            run_id=uuid4(),
            version=version,
            context=RunContext.SANDBOX,
            input_files=[
                ResolvedInputFile(name=name, content=content, field=field)
                for field, files in command.input_files_by_field.items()
                for name, content in files
            ],
            input_values={},
            memory_json=b'{"settings":{}}',
            action_payload=None,
        )
        run = make_tool_run(
            tool_id=version.tool_id,
            version_id=version.id,
            requested_by_user_id=actor.id,
            now=datetime.now(timezone.utc),
        )
        return ExecuteToolVersionResult(run=run, state_update=NoChangeStateUpdate())


def _docker_runner(artifacts_root: Path) -> DockerToolRunner:
    return DockerToolRunner(
        runner_image="skriptoteket-runner:latest",
        sandbox_timeout_seconds=60,
        production_timeout_seconds=60,
        limits=DockerRunnerLimits(
            cpu_limit=1.0,
            memory_limit="1g",
            pids_limit=256,
            tmpfs_tmp="rw,noexec,nosuid,nodev,size=256m,mode=1777",
        ),
        output_max_stdout_bytes=200_000,
        output_max_stderr_bytes=200_000,
        output_max_error_summary_bytes=20_000,
        capacity=RunnerCapacityLimiter(max_concurrency=1),
        artifacts=FilesystemArtifactManager(artifacts_root=artifacts_root),
        contract_selector=StaticRunnerContractSelector(
            contract=RunnerContract(
                request_factory=V3RunnerRequestFactory(), result_parser=V3RunnerResultParser()
            )
        ),
    )


async def _sandbox_run(*, bundle_files: dict[str, str], artifacts_root: Path) -> str:
    now = datetime.now(timezone.utc)
    actor = make_user(role=Role.ADMIN)
    tool_id, version_id, snapshot_id = uuid4(), uuid4(), uuid4()
    draft = gruppgenerator_draft(
        version_id=version_id, tool_id=tool_id, created_by_user_id=actor.id, now=now
    )
    execute = _RealRunnerExecute(draft=draft, runner=_docker_runner(artifacts_root))
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = draft
    versions.list_for_tool.return_value = []
    sessions = AsyncMock(spec=ToolSessionRepositoryProtocol)
    session = make_tool_session(
        tool_id=tool_id, user_id=actor.id, context=f"sandbox:{snapshot_id}", now=now
    )
    sessions.get_or_create.return_value = session
    sessions.update_state.return_value = session
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [snapshot_id, uuid4()]
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    session_files = AsyncMock(spec=SessionFileStorageProtocol)
    session_files.list_files.return_value = []
    handler = RunSandboxHandler(
        uow=FakeUow(),
        versions=versions,
        maintainers=AsyncMock(spec=ToolMaintainerRepositoryProtocol),
        sessions=sessions,
        id_generator=id_generator,
        execute=execute,
        session_files=session_files,
        locks=AsyncMock(spec=DraftLockRepositoryProtocol),
        clock=clock,
        snapshots=AsyncMock(spec=SandboxSnapshotRepositoryProtocol),
        settings=make_settings_mock(),
    )
    source_code, _ = gruppgenerator_files()

    await handler.handle(
        actor=actor,
        command=RunSandboxCommand(
            tool_id=tool_id,
            version_id=version_id,
            snapshot_payload=SandboxSnapshotPayload(
                entrypoint="run_tool", source_code=source_code, bundle_files=bundle_files
            ),
            input_files_by_field={"files": [("klass.csv", ROSTER_CSV)]},
        ),
    )

    assert execute.result is not None
    assert execute.result.status is RunStatus.SUCCEEDED, execute.result.stderr
    return execute.result.ui_result.model_dump_json()


@pytest.mark.asyncio
async def test_sandbox_run_executes_the_unsaved_roster_edit(tmp_path: Path) -> None:
    _, saved_bundle = gruppgenerator_files()
    edited_bundle = {**saved_bundle, "roster.py": edited_roster_py(saved_bundle["roster.py"])}

    saved_output = await _sandbox_run(bundle_files=saved_bundle, artifacts_root=tmp_path / "a")
    edited_output = await _sandbox_run(bundle_files=edited_bundle, artifacts_root=tmp_path / "b")

    assert "Anna Berg" in saved_output
    assert EDIT_MARKER not in saved_output
    assert f"{EDIT_MARKER} Anna Berg" in edited_output
