from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.input_files import normalize_input_files
from skriptoteket.domain.scripting.models import (
    RunStatus,
    ToolVersion,
    finish_run,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.observability.tracing import get_tracer, trace_operation
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

if TYPE_CHECKING:
    from opentelemetry.trace import Span

logger = structlog.get_logger(__name__)


def _format_syntax_error(exc: SyntaxError) -> str:
    parts: list[str] = [f"SyntaxError: {exc.msg}"]

    location_parts: list[str] = []
    if exc.lineno is not None:
        location_parts.append(f"line {exc.lineno}")
    if exc.offset is not None:
        location_parts.append(f"col {exc.offset}")
    if location_parts:
        parts[0] = f"{parts[0]} ({', '.join(location_parts)})"

    if exc.text:
        code_line = exc.text.rstrip("\n")
        parts.append(code_line)
        if exc.offset is not None:
            caret_position = max(exc.offset - 1, 0)
            parts.append(" " * caret_position + "^")

    return "\n".join(parts)


class ExecuteToolVersionHandler(ExecuteToolVersionHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        runner: ToolRunnerProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._uow = uow
        self._versions = versions
        self._runs = runs
        self._runner = runner
        self._ui_policy_provider = ui_policy_provider
        self._backend_actions = backend_actions
        self._ui_normalizer = ui_normalizer
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        command: ExecuteToolVersionCommand,
    ) -> ExecuteToolVersionResult:
        started_at = time.monotonic()
        version = await self._versions.get_by_id(version_id=command.version_id)
        if version is None:
            raise not_found("ToolVersion", str(command.version_id))
        if version.tool_id != command.tool_id:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message="ToolVersion does not belong to the specified Tool",
                details={
                    "tool_id": str(command.tool_id),
                    "version_id": str(command.version_id),
                    "version_tool_id": str(version.tool_id),
                },
            )

        profile_id = await self._ui_policy_provider.get_profile_id_for_tool(
            tool_id=command.tool_id,
            actor=actor,
        )
        policy = self._ui_policy_provider.get_policy(profile_id=profile_id)
        backend_actions_list = await self._backend_actions.list_backend_actions(
            tool_id=command.tool_id,
            actor=actor,
            policy=policy,
        )

        now = self._clock.now()
        run_id = self._id_generator.new_uuid()

        # Start tracing span for execution
        tracer = get_tracer("skriptoteket")
        with trace_operation(
            tracer,
            "execute_tool_version",
            {
                "tool.id": str(command.tool_id),
                "version.id": str(command.version_id),
                "run.id": str(run_id),
                "run.context": command.context.value,
                "actor.id": str(actor.id),
            },
        ) as span:
            return await self._execute_with_span(
                span=span,
                actor=actor,
                command=command,
                run_id=run_id,
                version=version,
                now=now,
                backend_actions_list=backend_actions_list,
                policy=policy,
                started_at=started_at,
            )

    async def _execute_with_span(
        self,
        *,
        span: Span,
        actor: User,
        command: ExecuteToolVersionCommand,
        run_id: UUID,
        version: ToolVersion,
        now: datetime,
        backend_actions_list: list[UiFormAction],
        policy: UiPolicy,
        started_at: float,
    ) -> ExecuteToolVersionResult:
        """Execute tool version with tracing span context."""
        normalized_input_files, input_manifest = normalize_input_files(
            input_files=command.input_files
        )
        primary_filename = normalized_input_files[0][0]
        total_size_bytes = sum(len(content) for _, content in normalized_input_files)

        run = start_tool_version_run(
            run_id=run_id,
            tool_id=command.tool_id,
            version_id=command.version_id,
            context=command.context,
            requested_by_user_id=actor.id,
            workdir_path=str(run_id),
            input_filename=primary_filename,
            input_size_bytes=total_size_bytes,
            input_manifest=input_manifest,
            now=now,
        )

        logger.info(
            "Tool execution started",
            run_id=str(run_id),
            tool_id=str(command.tool_id),
            tool_version_id=str(command.version_id),
            context=command.context.value,
            actor_id=str(actor.id),
            input_filename=primary_filename,
            input_files_count=len(normalized_input_files),
            input_size_bytes=total_size_bytes,
        )

        span.add_event("run_created", {"run_id": str(run_id)})
        span.set_attribute("run.input_files_count", len(normalized_input_files))
        span.set_attribute("run.input_total_size_bytes", total_size_bytes)

        async with self._uow:
            await self._runs.create(run=run)

        execution_result: ToolExecutionResult | None = None
        domain_error_to_raise: DomainError | None = None
        fallback_raw_result: ToolUiContractV2Result | None = None

        try:
            compile(version.source_code, "<tool_version>", "exec")
            execution_result = await self._runner.execute(
                run_id=run_id,
                version=version,
                context=command.context,
                input_files=normalized_input_files,
            )
        except SyntaxError as exc:
            logger.warning(
                "Tool execution failed (syntax error)",
                run_id=str(run_id),
                tool_id=str(command.tool_id),
                tool_version_id=str(command.version_id),
                context=command.context.value,
                actor_id=str(actor.id),
                error_message=exc.msg,
                lineno=exc.lineno,
                offset=exc.offset,
            )
            span.add_event("syntax_error", {"message": exc.msg or ""})
            syntax_error_summary = _format_syntax_error(exc)
            fallback_raw_result = ToolUiContractV2Result(
                status="failed",
                error_summary=syntax_error_summary,
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )
            execution_result = ToolExecutionResult(
                status=RunStatus.FAILED,
                stdout="",
                stderr="",
                ui_result=fallback_raw_result,
                artifacts_manifest=ArtifactsManifest(artifacts=[]),
            )
        except DomainError as exc:
            logger.warning(
                "Tool execution failed (domain error)",
                run_id=str(run_id),
                tool_id=str(command.tool_id),
                tool_version_id=str(command.version_id),
                context=command.context.value,
                actor_id=str(actor.id),
                error_code=exc.code.value,
            )
            span.add_event("domain_error", {"code": exc.code.value})
            domain_error_to_raise = exc
            fallback_raw_result = ToolUiContractV2Result(
                status="failed",
                error_summary=exc.message,
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Tool execution failed (unexpected exception)",
                run_id=str(run_id),
                tool_id=str(command.tool_id),
                tool_version_id=str(command.version_id),
                context=command.context.value,
                actor_id=str(actor.id),
            )
            span.add_event("internal_error")
            domain_error_to_raise = DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (internal error).",
            )
            fallback_raw_result = ToolUiContractV2Result(
                status="failed",
                error_summary="Execution failed (internal error).",
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )

        finish_now = self._clock.now()
        raw_result = (
            execution_result.ui_result if execution_result is not None else fallback_raw_result
        )
        if raw_result is None:
            raw_result = ToolUiContractV2Result(
                status="failed",
                error_summary=None,
                outputs=[],
                next_actions=[],
                state=None,
                artifacts=[],
            )

        normalization_result: UiNormalizationResult
        try:
            normalization_result = self._ui_normalizer.normalize(
                raw_result=raw_result,
                backend_actions=backend_actions_list,
                policy=policy,
            )
        except DomainError:
            logger.exception(
                "UI payload normalization failed",
                run_id=str(run_id),
                tool_id=str(command.tool_id),
                tool_version_id=str(command.version_id),
                context=command.context.value,
                actor_id=str(actor.id),
            )
            normalization_result = self._ui_normalizer.normalize(
                raw_result=ToolUiContractV2Result(
                    status="failed",
                    error_summary="Execution failed (ui_payload normalization error).",
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                ),
                backend_actions=backend_actions_list,
                policy=policy,
            )
            domain_error_to_raise = DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Execution failed (ui_payload normalization error).",
            )

        if execution_result is None:
            stdout = ""
            stderr = ""
            artifacts_manifest: dict[str, object] = {}
            if domain_error_to_raise is not None:
                stdout_candidate = domain_error_to_raise.details.get("stdout")
                if isinstance(stdout_candidate, str):
                    stdout = stdout_candidate
                stderr_candidate = domain_error_to_raise.details.get("stderr")
                if isinstance(stderr_candidate, str):
                    stderr = stderr_candidate
                artifacts_candidate = domain_error_to_raise.details.get("artifacts_manifest")
                if isinstance(artifacts_candidate, dict):
                    artifacts_manifest = artifacts_candidate

            run_error_summary = (
                None if domain_error_to_raise is None else domain_error_to_raise.message
            )
            finished = finish_run(
                run=run,
                status=RunStatus.FAILED,
                now=finish_now,
                stdout=stdout,
                stderr=stderr,
                artifacts_manifest=artifacts_manifest,
                error_summary=run_error_summary,
                ui_payload=normalization_result.ui_payload,
            )
        else:
            finished = finish_run(
                run=run,
                status=execution_result.status,
                now=finish_now,
                stdout=execution_result.stdout,
                stderr=execution_result.stderr,
                artifacts_manifest=execution_result.artifacts_manifest.model_dump(),
                error_summary=execution_result.ui_result.error_summary,
                ui_payload=normalization_result.ui_payload,
            )

        async with self._uow:
            await self._runs.update(run=finished)

        artifacts_count = 0
        artifacts = finished.artifacts_manifest.get("artifacts")
        if isinstance(artifacts, list):
            artifacts_count = len(artifacts)

        # Set final span attributes
        span.set_attribute("run.status", finished.status.value)
        span.set_attribute("run.artifacts_count", artifacts_count)
        span.set_attribute("run.duration_seconds", round(time.monotonic() - started_at, 6))

        logger.info(
            "Tool execution finished",
            run_id=str(run_id),
            tool_id=str(command.tool_id),
            tool_version_id=str(command.version_id),
            context=command.context.value,
            status=finished.status.value,
            duration_seconds=round(time.monotonic() - started_at, 6),
            artifacts_count=artifacts_count,
            error_summary_present=finished.error_summary is not None,
        )

        if domain_error_to_raise is not None:
            raise domain_error_to_raise

        return ExecuteToolVersionResult(run=finished, normalized_state=normalization_result.state)
