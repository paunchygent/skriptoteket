from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from skriptoteket.application.editor.prompt_composer import compose_system_prompt
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
from .preflight import maybe_apply_preflight_fallback
from .routing import resolve_model_for_counting


@dataclass(frozen=True, slots=True)
class PreflightContext:
    decision: ChatFailoverDecision
    prepared: PreparedOpsRequest | None
    prompt_messages_count: int
    system_prompt: str
    budget: ChatOpsBudget
    token_counter: TokenCounterProtocol
    model_for_counting: str


def resolve_system_prompt(
    *,
    template_id: str,
    settings: Settings,
    token_counter: TokenCounterProtocol,
    system_prompt_loader: Callable[[str], str] | None,
) -> str:
    if system_prompt_loader is not None:
        return system_prompt_loader(template_id)
    return compose_system_prompt(
        template_id=template_id,
        settings=settings,
        token_counter=token_counter,
    ).text


async def prepare_preflight_context(
    *,
    settings: Settings,
    providers: ChatOpsProvidersProtocol,
    budget_resolver: ChatOpsBudgetResolverProtocol,
    token_counters: TokenCounterResolverProtocol,
    failover: ChatFailoverRouterProtocol,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    command: EditOpsCommand,
    actor_id: UUID,
    decision: ChatFailoverDecision,
    template_id: str,
    system_prompt_loader: Callable[[str], str] | None,
    user_payload: str,
    capture_id: UUID | None,
    allow_remote_fallback: bool,
    message_len: int,
    virtual_files_bytes: int,
) -> PreflightContext:
    model_for_counting = resolve_model_for_counting(settings=settings, decision=decision)
    token_counter = token_counters.for_model(model=model_for_counting)

    system_prompt = resolve_system_prompt(
        template_id=template_id,
        settings=settings,
        token_counter=token_counter,
        system_prompt_loader=system_prompt_loader,
    )

    budget = budget_resolver.resolve_chat_ops_budget(provider=decision.provider)

    prepared, prompt_messages_count = await prepare_ops_request(
        uow=uow,
        sessions=sessions,
        turns=turns,
        messages=messages,
        tool_id=command.tool_id,
        user_id=actor_id,
        command_message=command.message,
        system_prompt=system_prompt,
        user_payload=user_payload,
        settings=settings,
        budget=budget,
        token_counter=token_counter,
        now=clock.now(),
        tail_limit=max(20, settings.LLM_CHAT_TAIL_MAX_MESSAGES),
        new_session_id=id_generator.new_uuid(),
        turn_id=id_generator.new_uuid(),
        user_message_id=id_generator.new_uuid(),
        assistant_message_id=id_generator.new_uuid(),
        correlation_id=capture_id,
    )

    preflight_outcome = await maybe_apply_preflight_fallback(
        prepared=prepared,
        prompt_messages_count=prompt_messages_count,
        decision=decision,
        system_prompt=system_prompt,
        budget=budget,
        token_counter=token_counter,
        model_for_counting=model_for_counting,
        settings=settings,
        providers=providers,
        budget_resolver=budget_resolver,
        token_counters=token_counters,
        system_prompt_loader=system_prompt_loader,
        template_id=template_id,
        command=command,
        actor_id=actor_id,
        allow_remote_fallback=allow_remote_fallback,
        failover=failover,
        uow=uow,
        sessions=sessions,
        turns=turns,
        messages=messages,
        clock=clock,
        id_generator=id_generator,
        user_payload=user_payload,
        capture_id=capture_id,
        message_len=message_len,
        virtual_files_bytes=virtual_files_bytes,
    )

    return PreflightContext(
        decision=preflight_outcome.decision,
        prepared=preflight_outcome.prepared,
        prompt_messages_count=preflight_outcome.prompt_messages_count,
        system_prompt=preflight_outcome.system_prompt,
        budget=preflight_outcome.budget,
        token_counter=preflight_outcome.token_counter,
        model_for_counting=preflight_outcome.model_for_counting,
    )
