from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

import httpx
import structlog
from structlog.contextvars import get_contextvars

from skriptoteket.application.editor.prompt_budget import apply_chat_budget, apply_chat_ops_budget
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
    VirtualFileId,
)
from skriptoteket.protocols.token_counter import TokenCounterProtocol, TokenCounterResolverProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
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
_VIRTUAL_FILE_IDS: tuple[VirtualFileId, ...] = (
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
)
_CHAT_USER_PAYLOAD_KIND = "editor_chat_user_payload"
_CHAT_USER_PAYLOAD_SCHEMA_VERSION = 1
_STREAM_FLUSH_MIN_CHARS = 256
_STREAM_FLUSH_MAX_INTERVAL_SECONDS = 0.75
_PENDING_TURN_ABANDONED_OUTCOME = "abandoned_by_new_request"


def _virtual_file_priority_high_to_low(*, active_file: VirtualFileId) -> list[VirtualFileId]:
    ordered: list[VirtualFileId] = []
    seen: set[VirtualFileId] = set()

    def add(file_id: VirtualFileId) -> None:
        if file_id in seen:
            return
        seen.add(file_id)
        ordered.append(file_id)

    add(active_file)
    for file_id in _VIRTUAL_FILE_IDS:
        add(file_id)
    return ordered


def _is_context_window_error(exc: httpx.HTTPStatusError) -> bool:
    response = exc.response
    if response is None:
        return False
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except (ValueError, httpx.ResponseNotRead):
        payload = None
    if payload is not None:
        haystack = str(payload)
    else:
        try:
            haystack = response.text
        except httpx.ResponseNotRead:
            return False
    return "exceed_context_size_error" in haystack.lower()


@dataclass(frozen=True, slots=True)
class _PreparedChatRequest:
    request: LLMChatRequest
    system_prompt: str
    tool_session_id: UUID
    turn_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    correlation_id: UUID | None


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
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_counters: TokenCounterResolverProtocol,
        system_prompt_loader: Callable[[str], str] | None = None,
    ) -> None:
        self._settings = settings
        self._providers = providers
        self._guard = guard
        self._failover = failover
        self._uow = uow
        self._sessions = sessions
        self._turns = turns
        self._messages = messages
        self._clock = clock
        self._id_generator = id_generator
        self._token_counters = token_counters
        self._system_prompt_loader = system_prompt_loader

    def _is_thread_expired(self, *, last_message_at: datetime) -> bool:
        return self._clock.now() - last_message_at > _THREAD_TTL

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

    def _build_chat_user_payload(
        self,
        *,
        message: str,
        active_file: VirtualFileId,
        virtual_files: dict[VirtualFileId, str],
        max_payload_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> tuple[str, list[VirtualFileId]]:
        ordered_files = _virtual_file_priority_high_to_low(active_file=active_file)
        included: list[VirtualFileId] = [active_file]
        for file_id in ordered_files:
            if file_id == active_file:
                continue
            included.append(file_id)

        while True:
            selected_files = {file_id: virtual_files.get(file_id, "") for file_id in included}
            omitted = [file_id for file_id in ordered_files if file_id not in included]
            payload_obj: dict[str, object] = {
                "kind": _CHAT_USER_PAYLOAD_KIND,
                "schema_version": _CHAT_USER_PAYLOAD_SCHEMA_VERSION,
                "message": message,
                "active_file": active_file,
                "virtual_files": selected_files,
                "omitted_virtual_file_ids": omitted,
            }
            payload = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
            payload_tokens = token_counter.count_chat_message(role="user", content=payload)
            if payload_tokens <= max_payload_tokens:
                return payload, included

            if len(included) <= 1:
                raise validation_error(_MESSAGE_TOO_LONG)
            included.pop()  # drop lowest priority until it fits

    async def _prepare_request(
        self,
        *,
        tool_id: UUID,
        actor: User,
        message: str,
        base_version_id: UUID | None,
        active_file: VirtualFileId | None,
        virtual_files: dict[VirtualFileId, str] | None,
        system_prompt: str,
        token_counter: TokenCounterProtocol,
        max_user_message_tokens: int,
    ) -> _PreparedChatRequest:
        correlation_id = self._current_correlation_id()
        turn_id = self._id_generator.new_uuid()
        user_message_id = self._id_generator.new_uuid()
        assistant_message_id = self._id_generator.new_uuid()

        if virtual_files is None:
            if (
                token_counter.count_chat_message(role="user", content=message)
                > max_user_message_tokens
            ):
                raise validation_error(_MESSAGE_TOO_LONG)
        else:
            effective_active_file = active_file or "tool.py"
            if effective_active_file not in _VIRTUAL_FILE_IDS:
                effective_active_file = "tool.py"

            payload, _ = self._build_chat_user_payload(
                message=message,
                active_file=effective_active_file,
                virtual_files=virtual_files,
                max_payload_tokens=max_user_message_tokens,
                token_counter=token_counter,
            )
            user_payload_message = ChatMessage(role="user", content=payload)
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

            tail_turns = await self._turns.list_tail(
                tool_session_id=session.id,
                limit=max(20, self._settings.LLM_CHAT_TAIL_MAX_MESSAGES),
            )
            if tail_turns and self._is_thread_expired(last_message_at=tail_turns[-1].created_at):
                await self._turns.delete_all(tool_session_id=session.id)
                if session.state:
                    session = await self._sessions.clear_state(
                        tool_id=tool_id,
                        user_id=actor.id,
                        context=_THREAD_CONTEXT,
                    )
                tail_turns = []

            if base_version_id is not None:
                session = await self._update_base_version_id(
                    tool_id=tool_id,
                    actor=actor,
                    session=session,
                    base_version_id=base_version_id,
                )

            await self._turns.cancel_pending_turn(
                tool_session_id=session.id,
                failure_outcome=_PENDING_TURN_ABANDONED_OUTCOME,
            )

            completed_turn_ids = [turn.id for turn in tail_turns if turn.status == "complete"]
            existing_rows = await self._messages.list_by_turn_ids(
                tool_session_id=session.id,
                turn_ids=completed_turn_ids,
            )
            existing_messages = [
                ChatMessage(role=row.role, content=row.content) for row in existing_rows
            ]

            if virtual_files is None:
                proposed = [*existing_messages, ChatMessage(role="user", content=message)]
                _, budgeted = apply_chat_budget(
                    system_prompt=system_prompt,
                    messages=proposed,
                    context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
                    max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
                    safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                    system_prompt_max_tokens=self._settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS,
                    token_counter=token_counter,
                )
                if not budgeted:
                    raise validation_error(_MESSAGE_TOO_LONG)
                request = LLMChatRequest(messages=budgeted)
            else:
                _, budgeted, fits = apply_chat_ops_budget(
                    system_prompt=system_prompt,
                    messages=existing_messages,
                    user_payload=user_payload_message.content,
                    context_window_tokens=self._settings.LLM_CHAT_CONTEXT_WINDOW_TOKENS,
                    max_output_tokens=self._settings.LLM_CHAT_MAX_TOKENS,
                    safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                    system_prompt_max_tokens=self._settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS,
                    token_counter=token_counter,
                )
                if not fits:
                    raise validation_error(_MESSAGE_TOO_LONG)
                request = LLMChatRequest(messages=[*budgeted, user_payload_message])

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
                content=message,
            )
            await self._messages.create_message(
                tool_session_id=session.id,
                turn_id=turn_id,
                message_id=assistant_message_id,
                role="assistant",
                content="",
                meta={"in_reply_to": str(user_message_id)},
            )

        return _PreparedChatRequest(
            request=request,
            system_prompt=system_prompt,
            tool_session_id=session.id,
            turn_id=turn_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            correlation_id=correlation_id,
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

            system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
            available_message_tokens = prompt_budget_tokens - system_prompt_tokens
            if available_message_tokens <= 0:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            max_user_message_tokens = available_message_tokens - 1
            if max_user_message_tokens <= 0:
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(message=_DISABLED_MESSAGE)
                )
                return

            prepared = await self._prepare_request(
                tool_id=command.tool_id,
                actor=actor,
                message=command.message,
                base_version_id=command.base_version_id,
                active_file=command.active_file,
                virtual_files=command.virtual_files,
                system_prompt=system_prompt,
                token_counter=token_counter,
                max_user_message_tokens=max_user_message_tokens,
            )
            request = prepared.request
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
                turn_id=str(prepared.turn_id),
                correlation_id=str(prepared.correlation_id) if prepared.correlation_id else None,
            )

            start = time.perf_counter()
            output_chars = 0
            saw_delta = False
            assistant_chunks: list[str] = []
            failure_outcome: str | None = None
            failure_status_code: int | None = None

            last_flush_at = time.monotonic()
            last_flushed_len = 0

            async def flush_assistant_content(*, force: bool = False) -> None:
                nonlocal last_flush_at, last_flushed_len
                content = "".join(assistant_chunks)
                if not force:
                    if len(content) - last_flushed_len < _STREAM_FLUSH_MIN_CHARS and (
                        time.monotonic() - last_flush_at < _STREAM_FLUSH_MAX_INTERVAL_SECONDS
                    ):
                        return
                if not force and len(content) == last_flushed_len:
                    return
                last_flush_at = time.monotonic()
                last_flushed_len = len(content)
                async with self._uow:
                    await self._messages.update_message_content_if_pending_turn(
                        tool_session_id=prepared.tool_session_id,
                        turn_id=prepared.turn_id,
                        message_id=prepared.assistant_message_id,
                        content=content,
                        correlation_id=prepared.correlation_id,
                    )

            async def finalize_turn(
                *,
                status: Literal["complete", "failed", "cancelled"],
                failure_outcome: str | None,
                provider: str | None,
            ) -> None:
                content = "".join(assistant_chunks)
                async with self._uow:
                    await self._messages.update_message_content_if_pending_turn(
                        tool_session_id=prepared.tool_session_id,
                        turn_id=prepared.turn_id,
                        message_id=prepared.assistant_message_id,
                        content=content,
                        correlation_id=prepared.correlation_id,
                    )
                    await self._turns.update_status(
                        turn_id=prepared.turn_id,
                        status=status,
                        correlation_id=prepared.correlation_id,
                        failure_outcome=failure_outcome,
                        provider=provider,
                    )

            yield EditorChatMetaEvent(
                data=EditorChatMetaData(
                    correlation_id=prepared.correlation_id,
                    turn_id=prepared.turn_id,
                    assistant_message_id=prepared.assistant_message_id,
                )
            )

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
                        await flush_assistant_content()
                        yield EditorChatDeltaEvent(data=EditorChatDeltaData(text=delta))
                finally:
                    await self._failover.release_inflight(provider=provider_key)
                await self._failover.record_success(provider=provider_key)
            except asyncio.CancelledError:
                await finalize_turn(
                    status="cancelled",
                    failure_outcome="cancelled",
                    provider=provider_key,
                )
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
                                await flush_assistant_content()
                                yield EditorChatDeltaEvent(data=EditorChatDeltaData(text=delta))
                        finally:
                            await self._failover.release_inflight(provider=provider_key)
                    except asyncio.CancelledError:
                        await finalize_turn(
                            status="cancelled",
                            failure_outcome="cancelled",
                            provider=provider_key,
                        )
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
                await finalize_turn(
                    status="failed",
                    failure_outcome=_REMOTE_FALLBACK_REQUIRED_CODE,
                    provider=provider_key,
                )
                yield EditorChatDoneEvent(
                    data=EditorChatDoneDisabledData(
                        message=_REMOTE_FALLBACK_REQUIRED_MESSAGE,
                        code=_REMOTE_FALLBACK_REQUIRED_CODE,
                    )
                )
                return

            if failure_outcome is not None:
                await finalize_turn(
                    status="failed",
                    failure_outcome=failure_outcome,
                    provider=provider_key,
                )
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

                yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="error"))
                return

            await finalize_turn(
                status="complete",
                failure_outcome=None,
                provider=provider_key,
            )
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
            yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="stop"))
        finally:
            await self._guard.release(user_id=actor.id, tool_id=command.tool_id)
