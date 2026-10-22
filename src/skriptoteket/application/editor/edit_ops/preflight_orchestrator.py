from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from skriptoteket.application.editor.prompt_composer import compose_system_prompt
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatOpsBudget,
    ChatOpsBudgetResolverProtocol,
    EditOpsCommand,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .persistence import PreparedOpsRequest, prepare_ops_request


@dataclass(frozen=True, slots=True)
class PreflightContext:
    prepared: PreparedOpsRequest | None
    prompt_messages_count: int
    system_prompt: str
    budget: ChatOpsBudget
    token_counter: TokenCounterProtocol


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
    budget_resolver: ChatOpsBudgetResolverProtocol,
    token_counters: TokenCounterResolverProtocol,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    clock: ClockProtocol,
    id_generator: IdGeneratorProtocol,
    command: EditOpsCommand,
    actor_id: UUID,
    template_id: str,
    system_prompt_loader: Callable[[str], str] | None,
    user_payload: str,
    capture_id: UUID | None,
) -> PreflightContext:
    token_counter = token_counters.for_model(model=settings.LLM_CHAT_OPS_MODEL)

    system_prompt = resolve_system_prompt(
        template_id=template_id,
        settings=settings,
        token_counter=token_counter,
        system_prompt_loader=system_prompt_loader,
    )

    budget = budget_resolver.resolve_chat_ops_budget()

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

    return PreflightContext(
        prepared=prepared,
        prompt_messages_count=prompt_messages_count,
        system_prompt=system_prompt,
        budget=budget,
        token_counter=token_counter,
    )
