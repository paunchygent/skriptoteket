from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

import structlog

from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverRouterProtocol,
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
    ChatOpsProvidersProtocol,
    EditOpsCommand,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .persistence import PreparedOpsRequest, prepare_ops_request
from .routing import can_use_fallback, resolve_fallback_model_for_counting

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PreflightOutcome:
    decision: ChatFailoverDecision
    prepared: PreparedOpsRequest | None
    prompt_messages_count: int
    system_prompt: str
    budget: ChatOpsBudget
    token_counter: TokenCounterProtocol
    model_for_counting: str


async def maybe_apply_preflight_fallback(
    *,
    prepared: PreparedOpsRequest | None,
    prompt_messages_count: int,
    decision: ChatFailoverDecision,
    system_prompt: str,
    budget: ChatOpsBudget,
    token_counter: TokenCounterProtocol,
    model_for_counting: str,
    settings: Settings,
    providers: ChatOpsProvidersProtocol,
    budget_resolver: ChatOpsBudgetResolverProtocol,
    token_counters: TokenCounterResolverProtocol,
    system_prompt_loader: Callable[[str], str] | None,
    template_id: str,
    command: EditOpsCommand,
    actor_id: UUID,
    allow_remote_fallback: bool,
    failover: ChatFailoverRouterProtocol,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    user_payload: str,
    capture_id: UUID | None,
    message_len: int,
    virtual_files_bytes: int,
) -> PreflightOutcome:
    if prepared is not None or decision.provider != "primary":
        return PreflightOutcome(
            decision=decision,
            prepared=prepared,
            prompt_messages_count=prompt_messages_count,
            system_prompt=system_prompt,
            budget=budget,
            token_counter=token_counter,
            model_for_counting=model_for_counting,
        )

    if not can_use_fallback(providers=providers, allow_remote_fallback=allow_remote_fallback):
        return PreflightOutcome(
            decision=decision,
            prepared=prepared,
            prompt_messages_count=prompt_messages_count,
            system_prompt=system_prompt,
            budget=budget,
            token_counter=token_counter,
            model_for_counting=model_for_counting,
        )

    fallback_model_for_counting = resolve_fallback_model_for_counting(settings=settings)
    fallback_token_counter = token_counters.for_model(model=fallback_model_for_counting)
    try:
        if system_prompt_loader is not None:
            fallback_system_prompt = system_prompt_loader(template_id)
        else:
            fallback_system_prompt = compose_system_prompt(
                template_id=template_id,
                settings=settings,
                token_counter=fallback_token_counter,
            ).text
    except (OSError, PromptTemplateError):
        return PreflightOutcome(
            decision=decision,
            prepared=prepared,
            prompt_messages_count=prompt_messages_count,
            system_prompt=system_prompt,
            budget=budget,
            token_counter=token_counter,
            model_for_counting=model_for_counting,
        )

    fallback_budget = budget_resolver.resolve_chat_ops_budget(provider="fallback")
    fallback_prepared, fallback_prompt_messages_count = await prepare_ops_request(
        uow=uow,
        sessions=sessions,
        turns=turns,
        messages=messages,
        tool_id=command.tool_id,
        user_id=actor_id,
        command_message=command.message,
        system_prompt=fallback_system_prompt,
        user_payload=user_payload,
        settings=settings,
        budget=fallback_budget,
        token_counter=fallback_token_counter,
        now=clock.now(),
        tail_limit=max(20, settings.LLM_CHAT_TAIL_MAX_MESSAGES),
        new_session_id=id_generator.new_uuid(),
        turn_id=id_generator.new_uuid(),
        user_message_id=id_generator.new_uuid(),
        assistant_message_id=id_generator.new_uuid(),
        correlation_id=capture_id,
    )
    if fallback_prepared is None:
        return PreflightOutcome(
            decision=decision,
            prepared=prepared,
            prompt_messages_count=prompt_messages_count,
            system_prompt=system_prompt,
            budget=budget,
            token_counter=token_counter,
            model_for_counting=model_for_counting,
        )

    decision = ChatFailoverDecision(provider="fallback", reason="preflight_over_budget")
    logger.info(
        "ai_chat_ops_preflight_failover",
        template_id=template_id,
        user_id=str(actor_id),
        tool_id=str(command.tool_id),
        from_provider="primary",
        to_provider="fallback",
        reason="preflight_over_budget",
        fallback_is_remote=providers.fallback_is_remote,
        allow_remote_fallback=allow_remote_fallback,
        primary_model=settings.LLM_CHAT_OPS_MODEL,
        fallback_model=fallback_model_for_counting,
        message_len=message_len,
        virtual_files_bytes=virtual_files_bytes,
    )
    await failover.mark_fallback_used(user_id=actor_id, tool_id=command.tool_id)

    return PreflightOutcome(
        decision=decision,
        prepared=fallback_prepared,
        prompt_messages_count=fallback_prompt_messages_count,
        system_prompt=fallback_system_prompt,
        budget=fallback_budget,
        token_counter=fallback_token_counter,
        model_for_counting=fallback_model_for_counting,
    )
