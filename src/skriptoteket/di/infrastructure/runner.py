"""Infrastructure provider: tool runner wiring and storage."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.config import Settings
from skriptoteket.infrastructure.runner.artifact_manager import FilesystemArtifactManager
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.docker.contract_selection import (
    RunnerContract,
    RunnerContractSelectorProtocol,
    StaticRunnerContractSelector,
)
from skriptoteket.infrastructure.runner.docker.request_factory import (
    RunnerRequestFactoryProtocol,
    V2RunnerRequestFactory,
)
from skriptoteket.infrastructure.runner.docker.result_parser import (
    RunnerResultParserProtocol,
    V2RunnerResultParser,
)
from skriptoteket.infrastructure.runner.docker_runner import DockerRunnerLimits, DockerToolRunner
from skriptoteket.infrastructure.runner.run_input_storage import LocalRunInputStorage
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import (
    ArtifactManagerProtocol,
    ToolRunnerAdoptionProtocol,
    ToolRunnerProtocol,
)


class InfrastructureRunnerProvider(Provider):
    """Provides tool runner services and storage bindings."""

    @provide(scope=Scope.APP)
    def runner_capacity(self, settings: Settings) -> RunnerCapacityLimiter:
        return RunnerCapacityLimiter(max_concurrency=settings.RUNNER_MAX_CONCURRENCY)

    @provide(scope=Scope.APP)
    def artifact_manager(self, settings: Settings) -> ArtifactManagerProtocol:
        return FilesystemArtifactManager(artifacts_root=settings.ARTIFACTS_ROOT)

    @provide(scope=Scope.APP)
    def run_input_storage(self, settings: Settings) -> RunInputStorageProtocol:
        return LocalRunInputStorage(artifacts_root=settings.ARTIFACTS_ROOT)

    @provide(scope=Scope.APP)
    def runner_request_factory(self) -> RunnerRequestFactoryProtocol:
        return V2RunnerRequestFactory()

    @provide(scope=Scope.APP)
    def runner_result_parser(self) -> RunnerResultParserProtocol:
        return V2RunnerResultParser()

    @provide(scope=Scope.APP)
    def runner_contract(
        self,
        request_factory: RunnerRequestFactoryProtocol,
        result_parser: RunnerResultParserProtocol,
    ) -> RunnerContract:
        return RunnerContract(request_factory=request_factory, result_parser=result_parser)

    @provide(scope=Scope.APP)
    def runner_contract_selector(
        self,
        contract: RunnerContract,
    ) -> RunnerContractSelectorProtocol:
        return StaticRunnerContractSelector(contract=contract)

    @provide(scope=Scope.APP)
    def tool_runner(
        self,
        settings: Settings,
        capacity: RunnerCapacityLimiter,
        artifacts: ArtifactManagerProtocol,
        contract_selector: RunnerContractSelectorProtocol,
    ) -> ToolRunnerProtocol:
        limits = DockerRunnerLimits(
            cpu_limit=settings.RUNNER_CPU_LIMIT,
            memory_limit=settings.RUNNER_MEMORY_LIMIT,
            pids_limit=settings.RUNNER_PIDS_LIMIT,
            tmpfs_tmp=settings.RUNNER_TMPFS_TMP,
        )
        return DockerToolRunner(
            runner_image=settings.RUNNER_IMAGE,
            sandbox_timeout_seconds=settings.RUNNER_TIMEOUT_SANDBOX_SECONDS,
            production_timeout_seconds=settings.RUNNER_TIMEOUT_PRODUCTION_SECONDS,
            limits=limits,
            output_max_stdout_bytes=settings.RUN_OUTPUT_MAX_STDOUT_BYTES,
            output_max_stderr_bytes=settings.RUN_OUTPUT_MAX_STDERR_BYTES,
            output_max_error_summary_bytes=settings.RUN_OUTPUT_MAX_ERROR_SUMMARY_BYTES,
            capacity=capacity,
            artifacts=artifacts,
            contract_selector=contract_selector,
        )

    @provide(scope=Scope.APP)
    def tool_runner_adoption(self, runner: ToolRunnerProtocol) -> ToolRunnerAdoptionProtocol:
        return runner  # type: ignore[return-value]
