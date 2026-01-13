from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import structlog

from skriptoteket.application.editor.chat_shared import (
    DISABLED_MESSAGE,
    IN_FLIGHT_MESSAGE,
    REMOTE_FALLBACK_REQUIRED_CODE,
    REMOTE_FALLBACK_REQUIRED_MESSAGE,
)
from skriptoteket.application.editor.chat_turn_preparer import ChatPromptBudgetUnavailable
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.editor_chat import (
    EditorChatStreamOrchestratorProtocol,
    EditorChatTurnPreparerProtocol,
)
from skriptoteket.protocols.llm import (
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatStreamProvidersProtocol,
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
        providers: ChatStreamProvidersProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        turn_preparer: EditorChatTurnPreparerProtocol,
        stream_orchestrator: EditorChatStreamOrchestratorProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._guard = guard
        self._failover = failover
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
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        guard_acquired = await self._guard.try_acquire(user_id=actor.id, tool_id=command.tool_id)
        if not guard_acquired:
            raise DomainError(code=ErrorCode.CONFLICT, message=IN_FLIGHT_MESSAGE)

        try:
            if not self._settings.LLM_CHAT_ENABLED:
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            if (
                not self._settings.LLM_CHAT_BASE_URL.strip()
                or not self._settings.LLM_CHAT_MODEL.strip()
            ):
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            template_id = self._settings.LLM_CHAT_TEMPLATE_ID

            decision = await self._failover.decide_route(
                user_id=actor.id,
                tool_id=command.tool_id,
                allow_remote_fallback=command.allow_remote_fallback,
                fallback_available=self._providers.fallback is not None,
                fallback_is_remote=self._providers.fallback_is_remote,
            )
            if decision.blocked == REMOTE_FALLBACK_REQUIRED_CODE:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(
                        message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
                        code=REMOTE_FALLBACK_REQUIRED_CODE,
                    )
                )
                return

            if decision.provider == "fallback":
                model_for_counting = (
                    self._settings.LLM_CHAT_FALLBACK_MODEL.strip() or self._settings.LLM_CHAT_MODEL
                )
            else:
                model_for_counting = self._settings.LLM_CHAT_MODEL
            token_counter = self._token_counters.for_model(model=model_for_counting)

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
                )
            except ChatPromptBudgetUnavailable:
                yield EditorChatDoneEvent(data=EditorChatDoneDisabledData(message=DISABLED_MESSAGE))
                return

            async for event in self._stream_orchestrator.stream(
                actor=actor,
                command=command,
                prepared=prepared,
                decision=decision,
                template_id=template_id,
            ):
                yield event
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
