from __future__ import annotations

import asyncio
from uuid import UUID

import structlog
from pydantic import JsonValue

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, ToolVersion
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol

from .adoption import try_adopt_sync
from .contract_selection import RunnerContractSelectorProtocol
from .execution import execute_sync
from .limits import DockerRunnerLimits

logger = structlog.get_logger(__name__)


class DockerToolRunner(ToolRunnerProtocol):
    def __init__(
        self,
        *,
        runner_image: str,
        sandbox_timeout_seconds: int,
        production_timeout_seconds: int,
        limits: DockerRunnerLimits,
        output_max_stdout_bytes: int,
        output_max_stderr_bytes: int,
        output_max_error_summary_bytes: int,
        capacity: RunnerCapacityLimiter,
        artifacts: ArtifactManagerProtocol,
        contract_selector: RunnerContractSelectorProtocol,
    ) -> None:
        self._runner_image = runner_image
        self._sandbox_timeout_seconds = sandbox_timeout_seconds
        self._production_timeout_seconds = production_timeout_seconds
        self._limits = limits
        self._output_max_stdout_bytes = output_max_stdout_bytes
        self._output_max_stderr_bytes = output_max_stderr_bytes
        self._output_max_error_summary_bytes = output_max_error_summary_bytes
        self._capacity = capacity
        self._artifacts = artifacts
        self._contract_selector = contract_selector

    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[tuple[str, bytes]],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult:
        if not await self._capacity.try_acquire():
            logger.warning(
                "Runner at capacity",
                run_id=str(run_id),
                tool_id=str(version.tool_id),
                tool_version_id=str(version.id),
                context=context.value,
            )
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Runner is at capacity; retry.",
            )

        try:
            contract = self._contract_selector.select(version=version, context=context)
            return await asyncio.to_thread(
                execute_sync,
                run_id=run_id,
                version=version,
                context=context,
                input_files=input_files,
                input_values=input_values,
                memory_json=memory_json,
                action_payload=action_payload,
                runner_image=self._runner_image,
                sandbox_timeout_seconds=self._sandbox_timeout_seconds,
                production_timeout_seconds=self._production_timeout_seconds,
                limits=self._limits,
                output_max_stdout_bytes=self._output_max_stdout_bytes,
                output_max_stderr_bytes=self._output_max_stderr_bytes,
                output_max_error_summary_bytes=self._output_max_error_summary_bytes,
                artifacts=self._artifacts,
                contract=contract,
            )
        finally:
            await self._capacity.release()

    async def try_adopt(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
    ) -> ToolExecutionResult | None:
        if not await self._capacity.try_acquire():
            logger.warning(
                "Runner at capacity (adopt)",
                run_id=str(run_id),
                tool_id=str(version.tool_id),
                tool_version_id=str(version.id),
                context=context.value,
            )
            raise DomainError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Runner is at capacity; retry.",
            )

        try:
            contract = self._contract_selector.select(version=version, context=context)
            return await asyncio.to_thread(
                try_adopt_sync,
                run_id=run_id,
                version=version,
                context=context,
                sandbox_timeout_seconds=self._sandbox_timeout_seconds,
                production_timeout_seconds=self._production_timeout_seconds,
                output_max_stdout_bytes=self._output_max_stdout_bytes,
                output_max_stderr_bytes=self._output_max_stderr_bytes,
                output_max_error_summary_bytes=self._output_max_error_summary_bytes,
                artifacts=self._artifacts,
                contract=contract,
            )
        finally:
            await self._capacity.release()
