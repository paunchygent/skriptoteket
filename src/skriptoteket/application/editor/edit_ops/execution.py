from __future__ import annotations

from dataclasses import dataclass

from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.edit_ops_payload_parser import EditOpsPayloadParserProtocol
from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    EditOpsCommand,
    EditOpsOp,
    EditorLlmProviderError,
    LLMChatOpsResponse,
    LLMChatRequest,
)

from .constants import (
    GENERATION_ERROR,
    INVALID_OPS_ERROR,
    MESSAGE_TOO_LONG,
    PATCH_ONLY_REQUIRED_ERROR,
)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    assistant_message: str
    ops: list[EditOpsOp]
    eval_outcome: str
    log_outcome: str
    finish_reason: str | None
    parse_ok: bool
    upstream_error: dict[str, object] | None
    raw_payload: object | None
    extracted_content: str | None


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
    provider: ChatOpsProviderProtocol,
    payload_parser: EditOpsPayloadParserProtocol,
    command: EditOpsCommand,
    request: LLMChatRequest,
    system_prompt: str,
    caller: AiDoorCaller,
) -> ExecutionResult:
    """Make the one door call and turn its answer into the edit-ops outcome.

    A provider failure becomes a failed outcome; ``AiDailyLimitReached`` is
    not caught here and reaches the flow.
    """

    try:
        response = await provider.complete_chat_ops(
            request=request,
            system_prompt=system_prompt,
            caller=caller,
        )
    except EditorLlmProviderError as error:
        return _provider_failure(error)
    return _answer_outcome(command=command, payload_parser=payload_parser, response=response)


def _provider_failure(error: EditorLlmProviderError) -> ExecutionResult:
    upstream_error: dict[str, object] = {
        "error_type": type(error).__name__,
        "kind": error.kind,
        "status_code": error.status_code,
        "detail": error.detail,
    }
    if error.kind == "context_window_exceeded":
        return ExecutionResult(
            assistant_message=MESSAGE_TOO_LONG,
            ops=[],
            eval_outcome="over_budget",
            log_outcome="over_budget",
            finish_reason=None,
            parse_ok=False,
            upstream_error=upstream_error,
            raw_payload=None,
            extracted_content=None,
        )
    return ExecutionResult(
        assistant_message=INVALID_OPS_ERROR,
        ops=[],
        eval_outcome="error",
        log_outcome="invalid_ops",
        finish_reason=None,
        parse_ok=False,
        upstream_error=upstream_error,
        raw_payload=None,
        extracted_content=None,
    )


def _answer_outcome(
    *,
    command: EditOpsCommand,
    payload_parser: EditOpsPayloadParserProtocol,
    response: LLMChatOpsResponse,
) -> ExecutionResult:
    assistant_message = GENERATION_ERROR
    ops: list[EditOpsOp] = []
    eval_outcome = "error"
    log_outcome = "error"
    parse_ok = False
    finish_reason = response.finish_reason
    if response.finish_reason == "length":
        eval_outcome = "truncated"
        log_outcome = "truncated"
    else:
        parsed = payload_parser.parse(raw=response.content)
        parse_ok = parsed is not None
        if parsed is None:
            assistant_message = INVALID_OPS_ERROR
            log_outcome = "parse_failed"
        elif not _ops_compatible_with_request(command=command, ops=parsed.ops):
            assistant_message = INVALID_OPS_ERROR
            log_outcome = "incompatible_ops"
        elif not _ops_are_patch_only(ops=parsed.ops):
            assistant_message = PATCH_ONLY_REQUIRED_ERROR
            log_outcome = "non_patch_ops"
        else:
            ops = parsed.ops
            assistant_message = parsed.assistant_message.strip() or assistant_message
            eval_outcome = "ok" if ops else "empty"
            log_outcome = eval_outcome

    return ExecutionResult(
        assistant_message=assistant_message,
        ops=ops,
        eval_outcome=eval_outcome,
        log_outcome=log_outcome,
        finish_reason=finish_reason,
        parse_ok=parse_ok,
        upstream_error=None,
        raw_payload=response.raw_payload,
        extracted_content=response.content,
    )
