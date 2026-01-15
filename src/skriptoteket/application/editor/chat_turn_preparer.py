from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.chat_shared import (
    BASE_VERSION_KEY,
    MESSAGE_TOO_LONG,
    PENDING_TURN_ABANDONED_OUTCOME,
    THREAD_CONTEXT,
    THREAD_TTL,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.editor_chat import (
    EditorChatPromptBuilderProtocol,
    EditorChatTurnPreparerProtocol,
    PreparedEditorChatRequest,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import ChatBudget, ChatMessage, EditorChatCommand
from skriptoteket.protocols.token_counter import TokenCounterProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


class ChatPromptBudgetUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class _ResolvedUserPayload:
    raw_message: str
    user_payload_message: ChatMessage | None


class EditorChatTurnPreparer(EditorChatTurnPreparerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        prompt_builder: EditorChatPromptBuilderProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._settings = settings
        self._prompt_builder = prompt_builder
        self._uow = uow
        self._sessions = sessions
        self._turns = turns
        self._messages = messages
        self._clock = clock
        self._id_generator = id_generator

    def _current_correlation_id(self) -> UUID | None:
        raw = get_contextvars().get("correlation_id")
        if isinstance(raw, UUID):
            return raw
        if isinstance(raw, str) and raw:
            try:
                return UUID(raw)
            except ValueError:
                return None
        return None

    def _is_thread_expired(self, *, last_message_at: datetime) -> bool:
        return self._clock.now() - last_message_at > THREAD_TTL

    async def _update_base_version_id(
        self,
        *,
        tool_id: UUID,
        actor: User,
        session: ToolSession,
        base_version_id: UUID,
    ) -> ToolSession:
        next_state = dict(session.state)
        next_state[BASE_VERSION_KEY] = str(base_version_id)

        for _attempt in range(2):
            try:
                return await self._sessions.update_state(
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=THREAD_CONTEXT,
                    expected_state_rev=session.state_rev,
                    state=next_state,
                )
            except DomainError as exc:
                if exc.code is not ErrorCode.CONFLICT:
                    raise

                refreshed = await self._sessions.get(
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=THREAD_CONTEXT,
                )
                if refreshed is None:
                    return session
                session = refreshed
                next_state = dict(session.state)
                next_state[BASE_VERSION_KEY] = str(base_version_id)

        return session

    def _resolve_user_payload(
        self,
        *,
        command: EditorChatCommand,
        system_prompt: str,
        token_counter: TokenCounterProtocol,
        budget: ChatBudget,
    ) -> _ResolvedUserPayload:
        max_user_message_tokens = self._prompt_builder.plan_max_user_message_tokens(
            system_prompt=system_prompt,
            token_counter=token_counter,
            budget=budget,
        )
        if max_user_message_tokens is None:
            raise ChatPromptBudgetUnavailable("prompt_budget_unavailable")

        if command.virtual_files is None:
            self._prompt_builder.validate_plain_user_message(
                message=command.message,
                max_user_message_tokens=max_user_message_tokens,
                token_counter=token_counter,
            )
            return _ResolvedUserPayload(raw_message=command.message, user_payload_message=None)

        user_payload_message = self._prompt_builder.build_user_payload_message(
            message=command.message,
            active_file=command.active_file,
            virtual_files=command.virtual_files,
            max_user_message_tokens=max_user_message_tokens,
            token_counter=token_counter,
        )
        return _ResolvedUserPayload(
            raw_message=command.message,
            user_payload_message=user_payload_message,
        )

    async def prepare(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
        system_prompt: str,
        token_counter: TokenCounterProtocol,
        budget: ChatBudget,
    ) -> PreparedEditorChatRequest:
        correlation_id = self._current_correlation_id()
        turn_id = self._id_generator.new_uuid()
        user_message_id = self._id_generator.new_uuid()
        assistant_message_id = self._id_generator.new_uuid()

        try:
            resolved = self._resolve_user_payload(
                command=command,
                system_prompt=system_prompt,
                token_counter=token_counter,
                budget=budget,
            )
        except ChatPromptBudgetUnavailable:
            system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
            prompt_budget_tokens = (
                budget.context_window_tokens
                - budget.max_output_tokens
                - self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS
            )
            logger.warning(
                "ai_chat_prompt_budget_unavailable",
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
                active_file=command.active_file,
                has_virtual_files=command.virtual_files is not None,
                context_window_tokens=budget.context_window_tokens,
                max_output_tokens=budget.max_output_tokens,
                safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                prompt_budget_tokens=prompt_budget_tokens,
                system_prompt_tokens=system_prompt_tokens,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            raise
        except DomainError as exc:
            if exc.code != ErrorCode.VALIDATION_ERROR or exc.message != MESSAGE_TOO_LONG:
                raise

            system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
            prompt_budget_tokens = (
                budget.context_window_tokens
                - budget.max_output_tokens
                - self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS
            )
            message_tokens = token_counter.count_chat_message(role="user", content=command.message)
            virtual_files_bytes = (
                sum(len(text.encode("utf-8")) for text in command.virtual_files.values())
                if command.virtual_files is not None
                else 0
            )
            max_user_message_tokens = (
                prompt_budget_tokens - system_prompt_tokens - 1
                if prompt_budget_tokens > system_prompt_tokens + 1
                else 0
            )
            logger.warning(
                "ai_chat_message_too_long",
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
                message_len=len(command.message),
                message_tokens=message_tokens,
                active_file=command.active_file,
                has_virtual_files=command.virtual_files is not None,
                virtual_files_bytes=virtual_files_bytes,
                context_window_tokens=budget.context_window_tokens,
                max_output_tokens=budget.max_output_tokens,
                safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                prompt_budget_tokens=prompt_budget_tokens,
                system_prompt_tokens=system_prompt_tokens,
                max_user_message_tokens=max_user_message_tokens,
                correlation_id=str(correlation_id) if correlation_id else None,
            )
            raise

        async with self._uow:
            session = await self._sessions.get(
                tool_id=command.tool_id,
                user_id=actor.id,
                context=THREAD_CONTEXT,
            )
            if session is None:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=command.tool_id,
                    user_id=actor.id,
                    context=THREAD_CONTEXT,
                )

            tail_turns = await self._turns.list_tail(
                tool_session_id=session.id,
                limit=max(20, self._settings.LLM_CHAT_TAIL_MAX_MESSAGES),
            )
            if tail_turns and self._is_thread_expired(last_message_at=tail_turns[-1].created_at):
                await self._turns.delete_all(tool_session_id=session.id)
                if session.state:
                    session = await self._sessions.clear_state(
                        tool_id=command.tool_id,
                        user_id=actor.id,
                        context=THREAD_CONTEXT,
                    )
                tail_turns = []

            if command.base_version_id is not None:
                session = await self._update_base_version_id(
                    tool_id=command.tool_id,
                    actor=actor,
                    session=session,
                    base_version_id=command.base_version_id,
                )

            await self._turns.cancel_pending_turn(
                tool_session_id=session.id,
                failure_outcome=PENDING_TURN_ABANDONED_OUTCOME,
            )

            completed_turn_ids = [turn.id for turn in tail_turns if turn.status == "complete"]
            existing_rows = await self._messages.list_by_turn_ids(
                tool_session_id=session.id,
                turn_ids=completed_turn_ids,
            )
            existing_messages = [
                ChatMessage(role=row.role, content=row.content) for row in existing_rows
            ]

            request = self._prompt_builder.build_llm_request(
                system_prompt=system_prompt,
                existing_messages=existing_messages,
                message=resolved.raw_message,
                user_payload_message=resolved.user_payload_message,
                token_counter=token_counter,
                budget=budget,
            )

            await self._turns.create_turn(
                turn_id=turn_id,
                tool_session_id=session.id,
                status="pending",
                provider=None,
                correlation_id=correlation_id,
            )
            await self._messages.create_message(
                tool_session_id=session.id,
                turn_id=turn_id,
                message_id=user_message_id,
                role="user",
                content=resolved.raw_message,
            )
            await self._messages.create_message(
                tool_session_id=session.id,
                turn_id=turn_id,
                message_id=assistant_message_id,
                role="assistant",
                content="",
                meta={"in_reply_to": str(user_message_id)},
            )

        return PreparedEditorChatRequest(
            request=request,
            system_prompt=system_prompt,
            tool_session_id=session.id,
            turn_id=turn_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            correlation_id=correlation_id,
        )
