from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from pydantic import JsonValue

from skriptoteket.application.scripting.commands import (
    ExecuteToolVersionCommand,
    ExecuteToolVersionResult,
)
from skriptoteket.application.scripting.run_input_resolution import ResolvedRunInputs
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import (
    RunStatus,
    ToolVersion,
    finish_run,
    start_tool_version_run,
)
from skriptoteket.domain.scripting.tool_settings import (
    compute_settings_session_context,
    normalize_tool_settings_values,
)
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result, UiFormAction
from skriptoteket.domain.scripting.ui.normalization import UiNormalizationResult
from skriptoteket.domain.scripting.ui.policy import UiPolicy
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.scripting_ui import UiPayloadNormalizerProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
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


async def execute_tool_version_pipeline(
    *,
    span: Span,
    actor: User,
    command: ExecuteToolVersionCommand,
    resolved_inputs: ResolvedRunInputs,
    normalized_input_values: dict[str, JsonValue],
    run_id: UUID,
    version: ToolVersion,
    now: datetime,
    backend_actions_list: list[UiFormAction],
    policy: UiPolicy,
    started_at: float,
    uow: UnitOfWorkProtocol,
    runs: ToolRunRepositoryProtocol,
    sessions: ToolSessionRepositoryProtocol,
    runner: ToolRunnerProtocol,
    ui_normalizer: UiPayloadNormalizerProtocol,
    promotion_applier: PromotionApplierProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
) -> ExecuteToolVersionResult:
    """Execute a tool version and persist run/session state."""
    input_manifest = resolved_inputs.manifest
    primary_filename = resolved_inputs.primary_filename
    total_size_bytes = resolved_inputs.total_size_bytes

    run = start_tool_version_run(
        run_id=run_id,
        tool_id=command.tool_id,
        version_id=command.version_id,
        snapshot_id=command.snapshot_id,
        context=command.context,
        requested_by_user_id=actor.id,
        session_context=command.session_context,
        workdir_path=str(run_id),
        input_filename=primary_filename,
        input_size_bytes=total_size_bytes,
        input_manifest=input_manifest,
        input_values=normalized_input_values,
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
        input_files_count=len(resolved_inputs.files),
        input_size_bytes=total_size_bytes,
    )

    span.add_event("run_created", {"run_id": str(run_id)})
    span.set_attribute("run.input_files_count", len(resolved_inputs.files))
    span.set_attribute("run.input_total_size_bytes", total_size_bytes)

    settings_values: dict[str, JsonValue] = {}
    memory_json = json.dumps(
        {"settings": settings_values},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    async with uow:
        await runs.create(run=run)
        if version.settings_schema is not None:
            context = command.settings_context or compute_settings_session_context(
                settings_schema=version.settings_schema
            )
            session = await sessions.get_or_create(
                session_id=id_generator.new_uuid(),
                tool_id=command.tool_id,
                user_id=actor.id,
                context=context,
            )

            try:
                settings_values = normalize_tool_settings_values(
                    settings_schema=version.settings_schema,
                    values=session.state,
                )
            except DomainError:
                logger.warning(
                    "Invalid persisted tool settings; ignoring",
                    run_id=str(run_id),
                    tool_id=str(command.tool_id),
                    tool_version_id=str(command.version_id),
                    actor_id=str(actor.id),
                )
                settings_values = {}

            memory_json = json.dumps(
                {"settings": settings_values},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

    execution_result: ToolExecutionResult | None = None
    domain_error_to_raise: DomainError | None = None
    fallback_raw_result: ToolUiContractV2Result | None = None

    try:
        compile(version.source_code, "<tool_version>", "exec")
        execution_result = await runner.execute(
            run_id=run_id,
            version=version,
            context=command.context,
            input_files=resolved_inputs.files,
            input_values=normalized_input_values,
            memory_json=memory_json,
            action_payload=command.action_payload,
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

    if execution_result is not None and execution_result.promotions is not None:
        if execution_result.promotions.requests:
            try:
                await _apply_promotions(
                    promotion_applier=promotion_applier,
                    run_id=run_id,
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=command.session_context,
                    execution_result=execution_result,
                )
            except DomainError as exc:
                domain_error_to_raise = DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Execution failed (promotion error).",
                    details={
                        "reason": exc.message,
                        "stdout": execution_result.stdout,
                        "stderr": execution_result.stderr,
                        "artifacts_manifest": execution_result.artifacts_manifest.model_dump(),
                    },
                )
                fallback_raw_result = ToolUiContractV2Result(
                    status="failed",
                    error_summary=domain_error_to_raise.message,
                    outputs=[],
                    next_actions=[],
                    state=None,
                    artifacts=[],
                )
                execution_result = None

    finish_now = clock.now()
    raw_result = execution_result.ui_result if execution_result is not None else fallback_raw_result
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
        normalization_result = ui_normalizer.normalize(
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
        normalization_result = ui_normalizer.normalize(
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

        run_error_summary = None if domain_error_to_raise is None else domain_error_to_raise.message
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

    async with uow:
        await runs.update(run=finished)

    artifacts_count = 0
    artifacts = finished.artifacts_manifest.get("artifacts")
    if isinstance(artifacts, list):
        artifacts_count = len(artifacts)

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

    return ExecuteToolVersionResult(run=finished, state_update=normalization_result.state_update)


async def _apply_promotions(
    *,
    promotion_applier: PromotionApplierProtocol,
    run_id: UUID,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    execution_result: ToolExecutionResult,
) -> None:
    if execution_result.status is not RunStatus.SUCCEEDED:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: promotions require succeeded status",
            details={"status": execution_result.status.value},
        )
    if execution_result.promotions is None:
        return
    await promotion_applier.apply_session_promotions(
        run_id=run_id,
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        artifacts_manifest=execution_result.artifacts_manifest,
        promotions=execution_result.promotions,
    )
