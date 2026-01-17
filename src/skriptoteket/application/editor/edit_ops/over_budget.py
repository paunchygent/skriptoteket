from __future__ import annotations

import time
from collections.abc import Mapping

import structlog

from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatOpsBudget,
    EditOpsCommand,
    EditOpsResult,
    PromptEvalMeta,
    VirtualFileId,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol

from .budgeting import build_over_budget_metrics
from .capture import CaptureContext
from .constants import MESSAGE_TOO_LONG
from .logging import EditOpsLogContext

logger = structlog.get_logger(__name__)


async def handle_over_budget(
    *,
    settings: Settings,
    actor: User,
    command: EditOpsCommand,
    decision: ChatFailoverDecision,
    model_for_counting: str,
    system_prompt: str,
    user_payload: str,
    budget: ChatOpsBudget,
    token_counter: TokenCounterProtocol,
    prompt_messages_count: int,
    base_hash: str,
    base_hashes: Mapping[VirtualFileId, str],
    base_fingerprints: Mapping[VirtualFileId, str],
    log_context: EditOpsLogContext,
    capture_context: CaptureContext,
) -> EditOpsResult:
    metrics = build_over_budget_metrics(
        settings=settings,
        system_prompt=system_prompt,
        user_payload=user_payload,
        budget=budget,
        token_counter=token_counter,
    )
    logger.warning(
        "ai_chat_ops_preflight_over_budget",
        template_id=log_context.template_id,
        user_id=str(actor.id),
        tool_id=str(command.tool_id),
        provider=decision.provider,
        failover_reason=decision.reason,
        model=model_for_counting,
        context_window_tokens=budget.context_window_tokens,
        max_output_tokens=budget.max_output_tokens,
        safety_margin_tokens=settings.LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS,
        prompt_budget_tokens=metrics.prompt_budget_tokens,
        system_prompt_tokens=metrics.system_prompt_tokens,
        user_payload_chars=len(user_payload),
        user_payload_tokens=metrics.user_payload_tokens,
        available_history_tokens=metrics.available_history_tokens,
        message_len=log_context.message_len,
        virtual_files_bytes=log_context.virtual_files_bytes,
    )
    log_context.log_result(
        provider=decision.provider,
        failover_reason=decision.reason,
        system_prompt_chars=len(system_prompt),
        prompt_messages_count=prompt_messages_count,
        finish_reason=None,
        parse_ok=False,
        ops_count=0,
        outcome="over_budget",
    )
    elapsed_ms = int((time.monotonic() - log_context.started_at) * 1000)
    await capture_context.capture_on_error(
        payload={
            "outcome": "over_budget",
            "stage": "preflight_budget",
            "template_id": log_context.template_id,
            "user_id": str(actor.id),
            "tool_id": str(command.tool_id),
            "provider": decision.provider,
            "failover_reason": decision.reason,
            "fallback_is_remote": log_context.fallback_is_remote,
            "allow_remote_fallback": log_context.allow_remote_fallback,
            "message_len": log_context.message_len,
            "virtual_files_bytes": log_context.virtual_files_bytes,
            "base_hash": base_hash,
            "base_hashes": base_hashes,
            "base_fingerprints": base_fingerprints,
            "system_prompt_chars": len(system_prompt),
            "system_prompt_tokens": metrics.system_prompt_tokens,
            "user_payload_chars": len(user_payload),
            "user_payload_tokens": metrics.user_payload_tokens,
            "context_window_tokens": budget.context_window_tokens,
            "max_output_tokens": budget.max_output_tokens,
            "prompt_messages_count": prompt_messages_count,
            "elapsed_ms": elapsed_ms,
        }
    )
    return EditOpsResult(
        enabled=True,
        assistant_message=MESSAGE_TOO_LONG,
        ops=[],
        base_fingerprints=base_fingerprints,
        eval_meta=PromptEvalMeta(
            template_id=log_context.template_id,
            outcome="over_budget",
            system_prompt_chars=len(system_prompt),
        ),
    )
