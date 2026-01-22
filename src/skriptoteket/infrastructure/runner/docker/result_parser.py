from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from .protocols import DockerContainerProtocol
from .results import parse_runner_payload


@dataclass(frozen=True, slots=True)
class RunnerParsedResult:
    status: RunStatus
    ui_result: ToolUiContractV2Result
    artifacts_manifest: ArtifactsManifest


class RunnerResultParserProtocol(Protocol):
    def parse(
        self,
        *,
        container: DockerContainerProtocol,
        result_json_bytes: bytes,
        run_id: UUID,
        stdout: str,
        stderr: str,
        artifacts: ArtifactManagerProtocol,
        output_max_error_summary_bytes: int,
    ) -> RunnerParsedResult: ...


class V2RunnerResultParser:
    def parse(
        self,
        *,
        container: DockerContainerProtocol,
        result_json_bytes: bytes,
        run_id: UUID,
        stdout: str,
        stderr: str,
        artifacts: ArtifactManagerProtocol,
        output_max_error_summary_bytes: int,
    ) -> RunnerParsedResult:
        status, ui_result, artifacts_manifest = parse_runner_payload(
            container=container,
            result_json_bytes=result_json_bytes,
            run_id=run_id,
            stdout=stdout,
            stderr=stderr,
            artifacts=artifacts,
            output_max_error_summary_bytes=output_max_error_summary_bytes,
        )
        return RunnerParsedResult(
            status=status,
            ui_result=ui_result,
            artifacts_manifest=artifacts_manifest,
        )
