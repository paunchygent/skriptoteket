from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.commands import ExecuteToolVersionCommand
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    ExecuteToolVersionHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import (
    ArtifactsManifest,
    StoredArtifact,
    ToolExecutionResult,
)
from skriptoteket.domain.scripting.models import (
    RunContext,
    RunStatus,
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    def __init__(self) -> None:
        self.active = False
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> UnitOfWorkProtocol:
        self.active = True
        self.enter_count += 1
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self.active = False
        self.exit_count += 1


def make_tool_version(*, tool_id: UUID, now: datetime, state: VersionState) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>ok</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=uuid4(),
        tool_id=tool_id,
        version_number=1,
        state=state,
        source_code=source_code,
        entrypoint=entrypoint,
        content_hash=compute_content_hash(entrypoint=entrypoint, source_code=source_code),
        derived_from_version_id=None,
        created_by_user_id=uuid4(),
        created_at=now,
        submitted_for_review_by_user_id=None,
        submitted_for_review_at=None,
        reviewed_by_user_id=None,
        reviewed_at=None,
        published_by_user_id=None,
        published_at=None,
        change_summary=None,
        review_note=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_commits_before_runner_execute(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    version = make_tool_version(tool_id=tool_id, now=now, state=VersionState.DRAFT)
    run_id = uuid4()

    uow = FakeUow()
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions_repo.get_by_id.return_value = version

    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = run_id

    clock = Mock(spec=ClockProtocol)
    clock.now.side_effect = [now, now]

    runner = AsyncMock(spec=ToolRunnerProtocol)
    execution_result = ToolExecutionResult(
        status=RunStatus.SUCCEEDED,
        stdout="ok",
        stderr="",
        html_output="<p>ok</p>",
        error_summary=None,
        artifacts_manifest=ArtifactsManifest(
            artifacts=[
                StoredArtifact(artifact_id="output_report_txt", path="output/report.txt", bytes=5)
            ]
        ),
    )

    async def _execute(
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_filename: str,
        input_bytes: bytes,
    ) -> ToolExecutionResult:
        del run_id, version, context, input_filename, input_bytes
        assert uow.active is False
        return execution_result

    runner.execute.side_effect = _execute

    handler = ExecuteToolVersionHandler(
        uow=uow,
        versions=versions_repo,
        runs=runs_repo,
        runner=runner,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=ExecuteToolVersionCommand(
            tool_id=tool_id,
            version_id=version.id,
            context=RunContext.SANDBOX,
            input_filename="input.txt",
            input_bytes=b"data",
        ),
    )

    assert result.run.status is RunStatus.SUCCEEDED
    assert uow.enter_count == 2
    assert uow.exit_count == 2
    runs_repo.create.assert_awaited_once()
    runs_repo.update.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_marks_failed_on_capacity_error(now: datetime) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    version = make_tool_version(tool_id=tool_id, now=now, state=VersionState.DRAFT)

    uow = FakeUow()
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions_repo.get_by_id.return_value = version

    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    clock = Mock(spec=ClockProtocol)
    clock.now.side_effect = [now, now]

    runner = AsyncMock(spec=ToolRunnerProtocol)
    runner.execute.side_effect = DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Runner is at capacity; retry.",
    )

    handler = ExecuteToolVersionHandler(
        uow=uow,
        versions=versions_repo,
        runs=runs_repo,
        runner=runner,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=ExecuteToolVersionCommand(
                tool_id=tool_id,
                version_id=version.id,
                context=RunContext.SANDBOX,
                input_filename="input.txt",
                input_bytes=b"data",
            ),
        )

    assert exc_info.value.code is ErrorCode.SERVICE_UNAVAILABLE
    runs_repo.update.assert_awaited_once()
    updated_run = runs_repo.update.call_args.kwargs["run"]
    assert updated_run.status is RunStatus.FAILED
    assert updated_run.error_summary == "Runner is at capacity; retry."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_version_marks_failed_on_syntax_error_and_skips_runner(
    now: datetime,
) -> None:
    actor = make_user(user_id=uuid4())
    tool_id = uuid4()
    version = make_tool_version(tool_id=tool_id, now=now, state=VersionState.DRAFT).model_copy(
        update={
            "source_code": "def run_tool(input_path: str, output_dir: str) -> str\n"
            "    return '<p>ok</p>'\n"
        }
    )
    run_id = uuid4()

    uow = FakeUow()
    versions_repo = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions_repo.get_by_id.return_value = version

    runs_repo = AsyncMock(spec=ToolRunRepositoryProtocol)

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = run_id

    clock = Mock(spec=ClockProtocol)
    clock.now.side_effect = [now, now]

    runner = AsyncMock(spec=ToolRunnerProtocol)

    handler = ExecuteToolVersionHandler(
        uow=uow,
        versions=versions_repo,
        runs=runs_repo,
        runner=runner,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=ExecuteToolVersionCommand(
            tool_id=tool_id,
            version_id=version.id,
            context=RunContext.SANDBOX,
            input_filename="input.txt",
            input_bytes=b"data",
        ),
    )

    assert result.run.status is RunStatus.FAILED
    assert result.run.error_summary is not None
    assert "SyntaxError" in result.run.error_summary
    runner.execute.assert_not_awaited()
    assert uow.enter_count == 2
    assert uow.exit_count == 2
    runs_repo.create.assert_awaited_once()
    runs_repo.update.assert_awaited_once()
