from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

import httpx
import structlog
from pydantic import JsonValue

from skriptoteket.application.editor.prompt_budget import apply_chat_budget, estimate_text_tokens
from skriptoteket.application.editor.prompt_composer import (
    PromptTemplateError,
    compose_system_prompt,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.tool_sessions import ToolSession
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.llm import (
    ChatFailoverRouterProtocol,
    ChatInFlightGuardProtocol,
    ChatMessage,
    ChatStreamProvidersProtocol,
    EditorChatCommand,
    EditorChatDeltaData,
    EditorChatDeltaEvent,
    EditorChatDoneDisabledData,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatHandlerProtocol,
    EditorChatMetaData,
    EditorChatMetaEvent,
    EditorChatNoticeData,
    EditorChatNoticeEvent,
    EditorChatStreamEvent,
    LLMChatRequest,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)

_DISABLED_MESSAGE = "AI‑chat är inte tillgänglig just nu. Försök igen senare."
_REMOTE_FALLBACK_REQUIRED_MESSAGE = (
    "Lokala AI-modellen är inte tillgänglig. Tillåt externa API:er (OpenAI) för att fortsätta."
)
_REMOTE_FALLBACK_REQUIRED_CODE = "remote_fallback_required"
_MESSAGE_TOO_LONG = "För långt meddelande: korta ned eller starta en ny chatt."
_THREAD_CONTEXT = "editor_chat"
_THREAD_TTL = timedelta(days=30)
_IN_FLIGHT_MESSAGE = "En chatförfrågan pågår redan. Försök igen om en stund."
_BASE_VERSION_KEY = "base_version_id"


def _is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        payload = None
    haystack = str(payload) if payload is not None else response.text
    return "exceed_context_size_error" in haystack.lower()


class EditorChatHandler(EditorChatHandlerProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        providers: ChatStreamProvidersProtocol,
        guard: ChatInFlightGuardProtocol,
        failover: ChatFailoverRouterProtocol,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._guard = guard
        self._failover = failover
        self._uow = uow
        self._sessions = sessions
        self._messages = messages
        self._clock = clock
        self._id_generator = id_generator
        self._system_prompt_loader = system_prompt_loader or (
            lambda template_id: compose_system_prompt(
                template_id=template_id,
                settings=settings,
            ).text
        )

    def _is_thread_expired(self, *, last_message_at: datetime) -> bool:
        return self._clock.now() - last_message_at > _THREAD_TTL

    async def _update_base_version_id(
        self,
        *,
        tool_id: UUID,
        actor: User,
        session: ToolSession,
        base_version_id: UUID,
    ) -> ToolSession:
        next_state = dict(session.state)
        next_state[_BASE_VERSION_KEY] = str(base_version_id)

        for _attempt in range(2):
            try:
                return await self._sessions.update_state(
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=_THREAD_CONTEXT,
                    expected_state_rev=session.state_rev,
                    state=next_state,
                )
            except DomainError as exc:
                if exc.code is not ErrorCode.CONFLICT:
                    raise

                refreshed = await self._sessions.get(
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=_THREAD_CONTEXT,
                )
                if refreshed is None:
                    return session
                session = refreshed
                next_state = dict(session.state)
                next_state[_BASE_VERSION_KEY] = str(base_version_id)

        return session

    async def _persist_user_message(
        self,
        *,
        tool_id: UUID,
        actor: User,
        message: str,
        system_prompt: str,
        base_version_id: UUID | None,
    ) -> tuple[list[ChatMessage], UUID, UUID]:
        user_message_id = self._id_generator.new_uuid()
        user_message = ChatMessage(role="user", content=message, message_id=user_message_id)

        async with self._uow:
            session = await self._sessions.get(
                tool_id=tool_id,
                user_id=actor.id,
                context=_THREAD_CONTEXT,
            )
            if session is None:
                session = await self._sessions.get_or_create(
                    session_id=self._id_generator.new_uuid(),
                    tool_id=tool_id,
                    user_id=actor.id,
                    context=_THREAD_CONTEXT,
                )

            tail = await self._messages.list_tail(
                tool_session_id=session.id,
                limit=self._settings.LLM_CHAT_TAIL_MAX_MESSAGES,
            )
            if tail and self._is_thread_expired(last_message_at=tail[-1].created_at):
                await self._messages.delete_all(tool_session_id=session.id)
                if session.state:
                    session = await self._sessions.clear_state(
                        tool_id=tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                tail = []

            if base_version_id is not None:
                session = await self._update_base_version_id(
                    tool_id=tool_id,
                    actor=actor,
                    session=session,
                    base_version_id=base_version_id,
                )

            existing_messages = [
                ChatMessage(
                    role=message_row.role,
                    content=message_row.content,
                    message_id=message_row.message_id,
                )
                for message_row in tail
            ]
            proposed_messages = [*existing_messages, user_message]

            system_prompt, budgeted_messages = apply_chat_budget(
                system_prompt=system_prompt,
                messages=proposed_messages,
                context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
                max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
                safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                system_prompt_max_tokens=self._settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS,
            )

            if not budgeted_messages:
                raise validation_error(_MESSAGE_TOO_LONG)

            await self._messages.append_message(
                tool_session_id=session.id,
                message_id=user_message_id,
                role="user",
                content=message,
            )

        return budgeted_messages, user_message_id, session.id

    async def _persist_assistant_message(
        self,
        *,
        tool_id: UUID,
        actor: User,
        tool_session_id: UUID,
        expected_user_message_id: UUID,
        assistant_message: str,
        meta_extra: dict[str, JsonValue] | None = None,
    ) -> None:
        async with self._uow:
            user_message = await self._messages.get_by_message_id(
                tool_session_id=tool_session_id,
                message_id=expected_user_message_id,
            )
            meta: dict[str, JsonValue] = {"in_reply_to": str(expected_user_message_id)}
            if meta_extra:
                meta.update(meta_extra)
            if user_message is None:
                meta["orphaned"] = True
                logger.warning(
                    "ai_chat_assistant_persist_orphaned",
                    user_id=str(actor.id),
                    tool_id=str(tool_id),
                    reason="missing_user_message",
                )

            await self._messages.append_message(
                tool_session_id=tool_session_id,
                message_id=self._id_generator.new_uuid(),
                role="assistant",
                content=assistant_message,
                meta=meta,
            )

    async def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
    ) -> AsyncIterator[EditorChatStreamEvent]:
        require_at_least_role(user=actor, role=Role.CONTRIBUTOR)

        guard_acquired = await self._guard.try_acquire(user_id=actor.id, tool_id=command.tool_id)
        if not guard_acquired:
            raise DomainError(code=ErrorCode.CONFLICT, message=_IN_FLIGHT_MESSAGE)

        try:
            if not self._settings.LLM_CHAT_ENABLED:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            if (
                not self._settings.LLM_CHAT_BASE_URL.strip()
                or not self._settings.LLM_CHAT_MODEL.strip()
            ):
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            template_id = self._settings.LLM_CHAT_TEMPLATE_ID
            try:
                system_prompt = self._system_prompt_loader(template_id)
            except (OSError, PromptTemplateError):
                logger.warning(
                    "ai_chat_system_prompt_unavailable",
                    template_id=template_id,
                )
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            prompt_budget_tokens = (
                self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS
                - self._settings.LLM_CHAT_MAX_TOKENS
                - self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS
            )
            if prompt_budget_tokens <= 0:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            system_prompt_tokens = estimate_text_tokens(system_prompt)
            available_message_tokens = prompt_budget_tokens - system_prompt_tokens
            if available_message_tokens <= 0:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            if estimate_text_tokens(command.message) > available_message_tokens:
                raise validation_error(_MESSAGE_TOO_LONG)

            allow_remote_fallback = command.allow_remote_fallback
            decision = await self._failover.decide_route(
                user_id=actor.id,
                tool_id=command.tool_id,
                allow_remote_fallback=allow_remote_fallback,
                fallback_available=self._providers.fallback is not None,
                fallback_is_remote=self._providers.fallback_is_remote,
            )
            if decision.blocked == "remote_fallback_required":
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(
                        message=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                        code=_REMOTE_FALLBACK_REQUIRED_CODE,
                    )
                )
                return

            budgeted_messages, user_message_id, tool_session_id = await self._persist_user_message(
                tool_id=command.tool_id,
                actor=actor,
                message=command.message,
                system_prompt=system_prompt,
                base_version_id=command.base_version_id,
            )
            request = LLMChatRequest(messages=budgeted_messages)
            system_prompt_chars = len(system_prompt)
            messages_chars = sum(len(message.content) for message in request.messages)

            logger.info(
                "ai_chat_request",
                template_id=template_id,
                system_prompt_chars=system_prompt_chars,
                message_count=len(request.messages),
                messages_chars=messages_chars,
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
            )

            start = time.perf_counter()
            output_chars = 0
            saw_delta = False
            assistant_chunks: list[str] = []
            failure_outcome: str | None = None
            failure_status_code: int | None = None

            yield EditorChatMetaEvent(data=EditorChatMetaData())

            try:

                def is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
                    if exc.response is None:
                        return False
                    status = exc.response.status_code
                    return status == 429 or status >= 500

                NoticeVariant = Literal["info", "warning"]

                def notice_for(reason: str) -> tuple[str, NoticeVariant]:
                    if reason == "breaker_open":
                        return (
                            "Lokala modellen verkar nere. Använder externa API:er (OpenAI).",
                            "warning",
                        )
                    if reason == "load_shed":
                        return (
                            "Lokala modellen är hårt belastad. Använder externa API:er (OpenAI).",
                            "warning",
                        )
                    if reason == "sticky_fallback":
                        return (
                            "Fortsätter med externa API:er (OpenAI) för den här chatten.",
                            "info",
                        )
                    return (
                        "Använder externa API:er (OpenAI).",
                        "info",
                    )

                provider_key = decision.provider
                provider = (
                    self._providers.primary
                    if provider_key == "primary"
                    else self._providers.fallback
                )
                if provider is None:
                    provider_key = "primary"
                    provider = self._providers.primary

                if provider_key == "fallback":
                    await self._failover.mark_fallback_used(
                        user_id=actor.id, tool_id=command.tool_id
                    )
                    if self._providers.fallback_is_remote:
                        message, variant = notice_for(decision.reason)
                        yield EditorChatNoticeEvent(
                            data=EditorChatNoticeData(message=message, variant=variant)
                        )

                await self._failover.acquire_inflight(provider=provider_key)
                try:
                    async for delta in provider.stream_chat(
                        request=request,
                        system_prompt=system_prompt,
                    ):
                        if not delta:
                            continue
                        saw_delta = True
                        output_chars += len(delta)
                        assistant_chunks.append(delta)
                        yield EditorChatDeltaEvent(data=EditorChatDeltaData(text=delta))
                finally:
                    await self._failover.release_inflight(provider=provider_key)
                await self._failover.record_success(provider=provider_key)
            except asyncio.CancelledError:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                logger.info(
                    "ai_chat_cancelled",
                    template_id=template_id,
                    system_prompt_chars=system_prompt_chars,
                    message_count=len(request.messages),
                    messages_chars=messages_chars,
                    output_chars=output_chars,
                    user_id=str(actor.id),
                    tool_id=str(command.tool_id),
                    elapsed_ms=elapsed_ms,
                )
                raise
            except httpx.TimeoutException:
                failure_outcome = "timeout"
                await self._failover.record_failure(provider=provider_key)
                retryable = True
            except httpx.HTTPStatusError as exc:
                failure_outcome = "over_budget" if _is_context_window_error(exc) else "error"
                if exc.response is not None:
                    failure_status_code = exc.response.status_code
                retryable = is_retryable_status(exc)
                if retryable:
                    await self._failover.record_failure(provider=provider_key)
            except (httpx.RequestError, ValueError):
                failure_outcome = "error"
                await self._failover.record_failure(provider=provider_key)
                retryable = True

            if (
                failure_outcome is not None
                and not saw_delta
                and provider_key == "primary"
                and retryable
                and self._providers.fallback is not None
                and (allow_remote_fallback or not self._providers.fallback_is_remote)
            ):
                provider_key = "fallback"
                provider = self._providers.fallback
                if provider is not None:
                    await self._failover.mark_fallback_used(
                        user_id=actor.id, tool_id=command.tool_id
                    )
                    if self._providers.fallback_is_remote:
                        yield EditorChatNoticeEvent(
                            data=EditorChatNoticeData(
                                message=(
                                    "Byter till externa API:er (OpenAI) eftersom den lokala "
                                    "modellen inte svarade."
                                ),
                                variant="warning",
                            )
                        )
                    failure_outcome = None
                    failure_status_code = None
                    try:
                        await self._failover.acquire_inflight(provider=provider_key)
                        try:
                            async for delta in provider.stream_chat(
                                request=request,
                                system_prompt=system_prompt,
                            ):
                                if not delta:
                                    continue
                                saw_delta = True
                                output_chars += len(delta)
                                assistant_chunks.append(delta)
                                yield EditorChatDeltaEvent(data=EditorChatDeltaData(text=delta))
                        finally:
                            await self._failover.release_inflight(provider=provider_key)
                    except asyncio.CancelledError:
                        raise
                    except httpx.TimeoutException:
                        failure_outcome = "timeout"
                        await self._failover.record_failure(provider=provider_key)
                    except httpx.HTTPStatusError as exc:
                        failure_outcome = (
                            "over_budget" if _is_context_window_error(exc) else "error"
                        )
                        if exc.response is not None:
                            failure_status_code = exc.response.status_code
                        if is_retryable_status(exc):
                            await self._failover.record_failure(provider=provider_key)
                    except (httpx.RequestError, ValueError):
                        failure_outcome = "error"
                        await self._failover.record_failure(provider=provider_key)
                    else:
                        await self._failover.record_success(provider=provider_key)

            if (
                failure_outcome is not None
                and not saw_delta
                and provider_key == "primary"
                and self._providers.fallback is not None
                and self._providers.fallback_is_remote
                and not allow_remote_fallback
            ):
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(
                        message=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                        code=_REMOTE_FALLBACK_REQUIRED_CODE,
                    )
                )
                return

            if failure_outcome is not None:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                logger.info(
                    "ai_chat_failed",
                    template_id=template_id,
                    system_prompt_chars=system_prompt_chars,
                    message_count=len(request.messages),
                    messages_chars=messages_chars,
                    output_chars=output_chars,
                    user_id=str(actor.id),
                    tool_id=str(command.tool_id),
                    outcome=failure_outcome,
                    status_code=failure_status_code,
                    partial=saw_delta,
                    elapsed_ms=elapsed_ms,
                )

                if assistant_chunks:
                    assistant_message = "".join(assistant_chunks)
                    await self._persist_assistant_message(
                        tool_id=command.tool_id,
                        actor=actor,
                        tool_session_id=tool_session_id,
                        expected_user_message_id=user_message_id,
                        assistant_message=assistant_message,
                        meta_extra={
                            "partial": True,
                            "stream_outcome": failure_outcome,
                        },
                    )

                yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="error"))
                return

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "ai_chat_done",
                template_id=template_id,
                system_prompt_chars=system_prompt_chars,
                message_count=len(request.messages),
                messages_chars=messages_chars,
                output_chars=output_chars,
                user_id=str(actor.id),
                tool_id=str(command.tool_id),
                outcome="ok" if saw_delta else "empty",
                elapsed_ms=elapsed_ms,
            )

            if assistant_chunks:
                assistant_message = "".join(assistant_chunks)
                await self._persist_assistant_message(
                    tool_id=command.tool_id,
                    actor=actor,
                    tool_session_id=tool_session_id,
                    expected_user_message_id=user_message_id,
                    assistant_message=assistant_message,
                )
            yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="stop"))
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
