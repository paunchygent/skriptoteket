from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx

from skriptoteket.protocols.edit_ops_payload_parser import EditOpsPayloadParserProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverRouterProtocol,
    ChatOpsProvidersProtocol,
    EditOpsCommand,
    EditOpsOp,
    LLMChatRequest,
)

from .constants import (
    GENERATION_ERROR,
    INVALID_OPS_ERROR,
    PATCH_ONLY_REQUIRED_ERROR,
    REMOTE_FALLBACK_REQUIRED_MESSAGE,
)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    assistant_message: str
    ops: list[EditOpsOp]
    eval_outcome: str
    log_outcome: str
    finish_reason: str | None
    parse_ok: bool
    provider_key: str
    failover_reason: str | None
    upstream_error: dict[str, object] | None
    raw_payload: object | None
    extracted_content: str | None
    requires_remote_fallback: bool


def _is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except (ValueError, httpx.ResponseNotRead):
        payload = None
    if payload is not None:
        haystack = str(payload)
    else:
        try:
            haystack = response.text
        except httpx.ResponseNotRead:
            return False
    return "exceed_context_size_error" in haystack.lower()


def _is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
    if exc.response is None:
        return False
    status = exc.response.status_code
    return status == 429 or status >= 500


def _ops_compatible_with_request(*, command: EditOpsCommand, ops: list[EditOpsOp]) -> bool:
    for op in ops:
        if hasattr(op, "target") and op.target.kind in {"cursor", "selection"}:
            if op.target_file != command.active_file:
                return False

        if hasattr(op, "target") and op.target.kind == "cursor":
            if command.cursor is None:
                return False

        if hasattr(op, "target") and op.target.kind == "selection":
            if command.selection is None:
                return False

    return True


def _ops_are_patch_only(*, ops: list[EditOpsOp]) -> bool:
    return all(op.op == "patch" for op in ops)


async def execute_chat_ops(
    *,
    providers: ChatOpsProvidersProtocol,
    failover: ChatFailoverRouterProtocol,
    payload_parser: EditOpsPayloadParserProtocol,
    command: EditOpsCommand,
    request: LLMChatRequest,
    system_prompt: str,
    decision: ChatFailoverDecision,
    allow_remote_fallback: bool,
    user_id: UUID,
) -> ExecutionResult:
    assistant_message = GENERATION_ERROR
    ops: list[EditOpsOp] = []
    eval_outcome = "error"
    log_outcome = "error"
    finish_reason: str | None = None
    parse_ok = False
    provider_key = decision.provider
    failover_reason: str | None = decision.reason
    upstream_error: dict[str, object] | None = None

    async def complete(provider_key: str):
        provider = providers.primary if provider_key == "primary" else providers.fallback
        if provider is None:
            raise ValueError("Fallback provider is not configured")

        await failover.acquire_inflight(provider=provider_key)  # type: ignore[arg-type]
        try:
            return await provider.complete_chat_ops(
                request=request,
                system_prompt=system_prompt,
            )
        finally:
            await failover.release_inflight(provider=provider_key)  # type: ignore[arg-type]

    if provider_key == "fallback":
        await failover.mark_fallback_used(user_id=user_id, tool_id=command.tool_id)

    response = None
    first_error: Exception | None = None
    try:
        response = await complete(provider_key)
    except httpx.TimeoutException as exc:
        first_error = exc
        eval_outcome = "timeout"
        log_outcome = "timeout"
        await failover.record_failure(provider=provider_key)
    except httpx.HTTPStatusError as exc:
        first_error = exc
        eval_outcome = "over_budget" if _is_context_window_error(exc) else "error"
        log_outcome = eval_outcome
        upstream_error = {
            "error_type": type(exc).__name__,
            "status_code": exc.response.status_code if exc.response is not None else None,
        }
        if exc.response is not None:
            try:
                upstream_error["payload"] = exc.response.json()
            except ValueError:
                upstream_error["payload"] = exc.response.text[:2000]
        if _is_retryable_status(exc):
            await failover.record_failure(provider=provider_key)
    except (httpx.RequestError, ValueError) as exc:
        first_error = exc
        eval_outcome = "error"
        log_outcome = "error"
        upstream_error = {
            "error_type": type(exc).__name__,
        }
        await failover.record_failure(provider=provider_key)
    else:
        await failover.record_success(provider=provider_key)

    can_use_fallback = providers.fallback is not None and (
        allow_remote_fallback or not providers.fallback_is_remote
    )
    retryable_primary_failure = (
        response is None
        and provider_key == "primary"
        and (
            isinstance(first_error, (httpx.TimeoutException, httpx.RequestError, ValueError))
            or (
                isinstance(first_error, httpx.HTTPStatusError) and _is_retryable_status(first_error)
            )
        )
    )

    if (
        retryable_primary_failure
        and providers.fallback is not None
        and providers.fallback_is_remote
        and not allow_remote_fallback
    ):
        return ExecutionResult(
            assistant_message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
            ops=[],
            eval_outcome="error",
            log_outcome="error",
            finish_reason=None,
            parse_ok=False,
            provider_key=provider_key,
            failover_reason=failover_reason,
            upstream_error=upstream_error,
            raw_payload=None,
            extracted_content=None,
            requires_remote_fallback=True,
        )

    if retryable_primary_failure and can_use_fallback:
        provider_key = "fallback"
        failover_reason = "retryable_primary_failure"
        await failover.mark_fallback_used(user_id=user_id, tool_id=command.tool_id)
        try:
            response = await complete(provider_key)
        except httpx.TimeoutException:
            eval_outcome = "timeout"
            log_outcome = "timeout"
            upstream_error = {"error_type": "TimeoutException"}
            await failover.record_failure(provider=provider_key)
        except httpx.HTTPStatusError as exc:
            eval_outcome = "over_budget" if _is_context_window_error(exc) else "error"
            log_outcome = eval_outcome
            upstream_error = {
                "error_type": type(exc).__name__,
                "status_code": exc.response.status_code if exc.response is not None else None,
            }
            if exc.response is not None:
                try:
                    upstream_error["payload"] = exc.response.json()
                except ValueError:
                    upstream_error["payload"] = exc.response.text[:2000]
            if _is_retryable_status(exc):
                await failover.record_failure(provider=provider_key)
        except (httpx.RequestError, ValueError):
            eval_outcome = "error"
            log_outcome = "error"
            upstream_error = {"error_type": "RequestError"}
            await failover.record_failure(provider=provider_key)
        else:
            await failover.record_success(provider=provider_key)

    if response is not None:
        finish_reason = response.finish_reason
        if response.finish_reason == "length":
            eval_outcome = "truncated"
            log_outcome = "truncated"
        else:
            parsed = payload_parser.parse(raw=response.content)
            parse_ok = parsed is not None
            if parsed is None:
                assistant_message = INVALID_OPS_ERROR
                eval_outcome = "error"
                log_outcome = "parse_failed"
            elif not _ops_compatible_with_request(command=command, ops=parsed.ops):
                ops = []
                assistant_message = INVALID_OPS_ERROR
                eval_outcome = "error"
                log_outcome = "incompatible_ops"
            elif not _ops_are_patch_only(ops=parsed.ops):
                ops = []
                assistant_message = PATCH_ONLY_REQUIRED_ERROR
                eval_outcome = "error"
                log_outcome = "non_patch_ops"
            else:
                ops = parsed.ops
                assistant_message = parsed.assistant_message.strip() or assistant_message
                eval_outcome = "ok" if ops else "empty"
                log_outcome = eval_outcome
    else:
        ops = []
        assistant_message = INVALID_OPS_ERROR
        eval_outcome = "error"
        log_outcome = "invalid_ops"

    return ExecutionResult(
        assistant_message=assistant_message,
        ops=ops,
        eval_outcome=eval_outcome,
        log_outcome=log_outcome,
        finish_reason=finish_reason,
        parse_ok=parse_ok,
        provider_key=provider_key,
        failover_reason=failover_reason,
        upstream_error=upstream_error,
        raw_payload=response.raw_payload if response is not None else None,
        extracted_content=response.content if response is not None else None,
        requires_remote_fallback=False,
    )
