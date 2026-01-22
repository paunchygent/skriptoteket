from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import (
    ToolVersion,
    VersionState,
    compute_content_hash,
)
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.docker.contract_selection import (
    RunnerContract,
    StaticRunnerContractSelector,
)
from skriptoteket.infrastructure.runner.docker.request_factory import V2RunnerRequestFactory
from skriptoteket.infrastructure.runner.docker.result_parser import V2RunnerResultParser
from skriptoteket.infrastructure.runner.docker_runner import (
    DockerRunnerLimits,
    DockerToolRunner,
)
from skriptoteket.protocols.runner import ArtifactManagerProtocol


@pytest.fixture
def runner_request_factory() -> V2RunnerRequestFactory:
    return V2RunnerRequestFactory()


@pytest.fixture
def runner_result_parser() -> V2RunnerResultParser:
    return V2RunnerResultParser()


@pytest.fixture
def runner_contract(
    runner_request_factory: V2RunnerRequestFactory,
    runner_result_parser: V2RunnerResultParser,
) -> RunnerContract:
    return RunnerContract(
        request_factory=runner_request_factory,
        result_parser=runner_result_parser,
    )


@pytest.fixture
def contract_selector(
    runner_contract: RunnerContract,
) -> StaticRunnerContractSelector:
    return StaticRunnerContractSelector(contract=runner_contract)


@pytest.fixture
def tool_version(now: datetime) -> ToolVersion:
    source_code = "def run_tool(input_path: str, output_dir: str) -> str:\n    return '<p>Hi</p>'\n"
    entrypoint = "run_tool"
    return ToolVersion(
        id=uuid4(),
        tool_id=uuid4(),
        version_number=1,
        state=VersionState.DRAFT,
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


@pytest.fixture
def mock_capacity() -> MagicMock:
    capacity = MagicMock(spec=RunnerCapacityLimiter)
    capacity.try_acquire = AsyncMock(return_value=True)
    capacity.release = AsyncMock()
    return capacity


@pytest.fixture
def mock_artifacts() -> MagicMock:
    artifacts = MagicMock(spec=ArtifactManagerProtocol)
    artifacts.store_output_archive.return_value = ArtifactsManifest(artifacts=[])
    return artifacts


@pytest.fixture
def runner(
    mock_capacity: MagicMock,
    mock_artifacts: MagicMock,
    contract_selector: StaticRunnerContractSelector,
) -> DockerToolRunner:
    limits = DockerRunnerLimits(
        cpu_limit=1.0,
        memory_limit="256m",
        pids_limit=128,
        tmpfs_tmp="size=64m",
    )
    return DockerToolRunner(
        runner_image="skriptoteket-runner:unit-test",
        sandbox_timeout_seconds=30,
        production_timeout_seconds=60,
        limits=limits,
        output_max_stdout_bytes=2048,
        output_max_stderr_bytes=2048,
        output_max_error_summary_bytes=2048,
        capacity=mock_capacity,
        artifacts=mock_artifacts,
        contract_selector=contract_selector,
    )


@pytest.fixture
def mock_docker_client(monkeypatch) -> MagicMock:
    import docker

    mocked_from_env = MagicMock(name="from_env")
    mocked_from_env.return_value = MagicMock()
    monkeypatch.setattr(docker, "from_env", mocked_from_env)
    return mocked_from_env
