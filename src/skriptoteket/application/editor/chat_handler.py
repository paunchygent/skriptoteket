from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import structlog

from skriptoteket.application.editor.chat_shared import DISABLED_MESSAGE, IN_FLIGHT_MESSAGE
from skriptoteket.application.editor.chat_turn_preparer import ChatPromptBudgetUnavailable
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.editor_chat import (
    EditorChatStreamOrchestratorProtocol,
    EditorChatTurnPreparerProtocol,
)
from skriptoteket.protocols.llm import (
    ChatBudgetResolverProtocol,
    ChatInFlightGuardProtocol,
    EditorChatCommand,
    EditorChatDoneDisabledData,
    EditorChatDoneEvent,
    EditorChatHandlerProtocol,
    EditorChatStreamEvent,
)
from skriptoteket.protocols.token_counter import TokenCounterResolverProtocol

logger = structlog.get_logger(__name__)


class EditorChatHandler(EditorChatHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        guard: ChatInFlightGuardProtocol,
        budget_resolver: ChatBudgetResolverProtocol,
        turn_preparer: EditorChatTurnPreparerProtocol,
        stream_orchestrator: EditorChatStreamOrchestratorProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._guard = guard
        self._budget_resolver = budget_resolver
        self._turn_preparer = turn_preparer
        self._stream_orchestrator = stream_orchestrator
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

    async def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
    ) -> AsyncIterator[EditorChatStreamEvent]:
        guard_acquired = await self._guard.try_acquire(user_id=actor.id, tool_id=command.tool_id)
        if not guard_acquired:
            raise DomainError(code=ErrorCode.CONFLICT, message=IN_FLIGHT_MESSAGE)

        try:
            if not self._settings.LLM_CHAT_ENABLED:
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            template_id = self._settings.LLM_CHAT_TEMPLATE_ID
            token_counter = self._token_counters.for_model(model=self._settings.LLM_CHAT_MODEL)

            try:
                if self._system_prompt_loader is not None:
                    system_prompt = self._system_prompt_loader(template_id)
                else:
                    system_prompt = compose_system_prompt(
                        template_id=template_id,
                        settings=self._settings,
                        token_counter=token_counter,
                    ).text
            except (OSError, PromptTemplateError) as exc:
                logger.warning(
                    "ai_chat_system_prompt_unavailable",
                    template_id=template_id,
                    error_type=type(exc).__name__,
                )
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            try:
                prepared = await self._turn_preparer.prepare(
                    actor=actor,
                    command=command,
                    system_prompt=system_prompt,
                    token_counter=token_counter,
                    budget=self._budget_resolver.resolve_chat_budget(),
                )
            except ChatPromptBudgetUnavailable:
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            async for event in self._stream_orchestrator.stream(
                actor=actor,
                command=command,
                prepared=prepared,
                template_id=template_id,
            ):
                yield event
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
