from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.models import RunStatus
from skriptoteket.domain.scripting.promotions import (
    PromotionEnvelope,
    PromotionRequest,
    PromotionResult,
)
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from ..contracts.result_payload_v3 import PromotionEnvelopeV3, parse_runner_result_v3
from ..contracts.state_update_v3 import (
    StateUpdate,
    StateUpdateClear,
    StateUpdateNoChange,
    StateUpdateSet,
)
from .container_io import (
    store_output_archive,
    store_output_archive_safely,
    truncate_utf8_str,
)
from .protocols import DockerContainerProtocol


@dataclass(frozen=True, slots=True)
class RunnerParsedResult:
    status: RunStatus
    ui_result: ToolUiContractV2Result
    artifacts_manifest: ArtifactsManifest
    promotions: PromotionEnvelope | None


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


class V3RunnerResultParser:
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
        try:
            payload = parse_runner_result_v3(result_json_bytes=result_json_bytes)
        except DomainError as exc:
            artifacts_manifest = store_output_archive_safely(
                container=container,
                run_id=run_id,
                artifacts=artifacts,
            )
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (runner contract violation).",
                details={
                    "reason": "invalid result.json",
                    "validation": exc.details,
                    "stdout": stdout,
                    "stderr": stderr,
                    "artifacts_manifest": artifacts_manifest.model_dump(),
                },
            ) from exc
        status = RunStatus(payload.status)
        state = _state_from_update(payload.state_update)
        error_summary = (
            None
            if payload.error_summary is None
            else truncate_utf8_str(
                value=payload.error_summary,
                max_bytes=output_max_error_summary_bytes,
            )
        )
        ui_result = ToolUiContractV2Result(
            status=payload.status,
            error_summary=error_summary,
            outputs=payload.outputs,
            next_actions=payload.next_actions,
            state=state,
            artifacts=payload.artifacts,
        )

        try:
            artifacts_manifest = store_output_archive(
                container=container,
                run_id=run_id,
                reported_artifacts=payload.artifacts,
                artifacts=artifacts,
            )
        except DomainError:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (artifact extraction violation).",
                details={
                    "stdout": stdout,
                    "stderr": stderr,
                },
            )
        return RunnerParsedResult(
            status=status,
            ui_result=ui_result,
            artifacts_manifest=artifacts_manifest,
            promotions=_map_promotions(payload.promotions),
        )


def _state_from_update(update: StateUpdate) -> dict[str, JsonValue] | None:
    if isinstance(update, StateUpdateNoChange):
        return None
    if isinstance(update, StateUpdateClear):
        return {}
    if isinstance(update, StateUpdateSet):
        return update.state
    return None


def _map_promotions(promotions: PromotionEnvelopeV3 | None) -> PromotionEnvelope | None:
    if promotions is None:
        return None
    return PromotionEnvelope(
        requests=[
            PromotionRequest(
                request_id=request.request_id,
                kind=request.kind,
                source_path=request.source_path,
                name=request.name,
                ref=request.ref,
            )
            for request in promotions.requests
        ],
        results=[
            PromotionResult(
                request_id=result.request_id,
                status=result.status,
                ref=result.ref,
                reason=result.reason,
            )
            for result in promotions.results
        ],
    )
