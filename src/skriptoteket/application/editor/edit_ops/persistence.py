from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from skriptoteket.config import Settings
from skriptoteket.domain.scripting.tool_session_turns import ToolSessionTurnStatus
from skriptoteket.protocols.llm import ChatMessage, ChatOpsBudget
from skriptoteket.protocols.token_counter import TokenCounterProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

from .budgeting import apply_budget_preflight
from .constants import PENDING_TURN_ABANDONED_OUTCOME, THREAD_CONTEXT, THREAD_TTL


@dataclass(frozen=True, slots=True)
class PreparedOpsRequest:
    messages: list[ChatMessage]
    user_payload: str
    tool_session_id: UUID
    turn_id: UUID
    assistant_message_id: UUID
    correlation_id: UUID | None


async def prepare_ops_request(
    *,
    uow: UnitOfWorkProtocol,
    sessions: ToolSessionRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    tool_id: UUID,
    user_id: UUID,
    command_message: str,
    system_prompt: str,
    user_payload: str,
    settings: Settings,
    budget: ChatOpsBudget,
    token_counter: TokenCounterProtocol,
    now: datetime,
    tail_limit: int,
    new_session_id: UUID,
    turn_id: UUID,
    user_message_id: UUID,
    assistant_message_id: UUID,
    correlation_id: UUID | None,
) -> tuple[PreparedOpsRequest | None, int]:
    async with uow:
        session = await sessions.get(
            tool_id=tool_id,
            user_id=user_id,
            context=THREAD_CONTEXT,
        )
        if session is None:
            session = await sessions.get_or_create(
                session_id=new_session_id,
                tool_id=tool_id,
                user_id=user_id,
                context=THREAD_CONTEXT,
            )

        tail_turns = await turns.list_tail(
            tool_session_id=session.id,
            limit=tail_limit,
        )
        if tail_turns and now - tail_turns[-1].created_at > THREAD_TTL:
            await turns.delete_all(tool_session_id=session.id)
            if session.state:
                await sessions.clear_state(
                    tool_id=tool_id,
                    user_id=user_id,
                    context=THREAD_CONTEXT,
                )
            tail_turns = []

        await turns.cancel_pending_turn(
            tool_session_id=session.id,
            failure_outcome=PENDING_TURN_ABANDONED_OUTCOME,
        )

        completed_turn_ids = [turn.id for turn in tail_turns if turn.status == "complete"]
        existing_rows = await messages.list_by_turn_ids(
            tool_session_id=session.id,
            turn_ids=completed_turn_ids,
        )
        existing_messages = [
            ChatMessage(role=row.role, content=row.content) for row in existing_rows
        ]

        preflight = apply_budget_preflight(
            settings=settings,
            system_prompt=system_prompt,
            messages=existing_messages,
            user_payload=user_payload,
            budget=budget,
            token_counter=token_counter,
        )
        if not preflight.fits:
            return None, preflight.prompt_messages_count

        await turns.create_turn(
            turn_id=turn_id,
            tool_session_id=session.id,
            status="pending",
            provider=None,
            correlation_id=correlation_id,
        )
        await messages.create_message(
            tool_session_id=session.id,
            turn_id=turn_id,
            message_id=user_message_id,
            role="user",
            content=command_message,
        )
        await messages.create_message(
            tool_session_id=session.id,
            turn_id=turn_id,
            message_id=assistant_message_id,
            role="assistant",
            content="",
            meta={"in_reply_to": str(user_message_id)},
        )

    return (
        PreparedOpsRequest(
            messages=preflight.messages,
            user_payload=user_payload,
            tool_session_id=session.id,
            turn_id=turn_id,
            assistant_message_id=assistant_message_id,
            correlation_id=correlation_id,
        ),
        preflight.prompt_messages_count,
    )


async def update_turn_failure_with_message(
    *,
    uow: UnitOfWorkProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    tool_session_id: UUID,
    turn_id: UUID,
    assistant_message_id: UUID,
    assistant_message: str,
    provider: str,
    failure_outcome: str,
    correlation_id: UUID | None,
) -> None:
    async with uow:
        await messages.update_message_content_if_pending_turn(
            tool_session_id=tool_session_id,
            turn_id=turn_id,
            message_id=assistant_message_id,
            content=assistant_message,
            correlation_id=correlation_id,
        )
        await turns.update_status(
            turn_id=turn_id,
            status="failed",
            correlation_id=correlation_id,
            failure_outcome=failure_outcome,
            provider=provider,
        )


async def complete_turn(
    *,
    uow: UnitOfWorkProtocol,
    messages: ToolSessionMessageRepositoryProtocol,
    turns: ToolSessionTurnRepositoryProtocol,
    tool_session_id: UUID,
    turn_id: UUID,
    assistant_message_id: UUID,
    assistant_message: str,
    provider: str,
    outcome: str,
    correlation_id: UUID | None,
) -> ToolSessionTurnStatus:
    turn_status: ToolSessionTurnStatus = "complete" if outcome in {"ok", "empty"} else "failed"
    failure_outcome = None if turn_status == "complete" else outcome
    async with uow:
        await messages.update_message_content_if_pending_turn(
            tool_session_id=tool_session_id,
            turn_id=turn_id,
            message_id=assistant_message_id,
            content=assistant_message,
            correlation_id=correlation_id,
        )
        await turns.update_status(
            turn_id=turn_id,
            status=turn_status,
            correlation_id=correlation_id,
            failure_outcome=failure_outcome,
            provider=provider,
        )
    return turn_status
