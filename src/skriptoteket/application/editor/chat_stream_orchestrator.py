from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from typing import Literal

import httpx
import structlog

from skriptoteket.application.editor.chat_shared import (
    REMOTE_FALLBACK_REQUIRED_CODE,
    REMOTE_FALLBACK_REQUIRED_MESSAGE,
    STREAM_FLUSH_MAX_INTERVAL_SECONDS,
    STREAM_FLUSH_MIN_CHARS,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.editor_chat import (
    EditorChatStreamOrchestratorProtocol,
    PreparedEditorChatRequest,
)
from skriptoteket.protocols.llm import (
    ChatFailoverDecision,
    ChatFailoverRouterProtocol,
    ChatStreamProvidersProtocol,
    EditorChatCommand,
    EditorChatDeltaData,
    EditorChatDeltaEvent,
    EditorChatDoneDisabledData,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatMetaData,
    EditorChatMetaEvent,
    EditorChatNoticeData,
    EditorChatNoticeEvent,
    EditorChatStreamEvent,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


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


class EditorChatStreamOrchestrator(EditorChatStreamOrchestratorProtocol):
    def __init__(
        self,
        *,
        providers: ChatStreamProvidersProtocol,
        failover: ChatFailoverRouterProtocol,
        uow: UnitOfWorkProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> None:
        self._providers = providers
        self._failover = failover
        self._uow = uow
        self._turns = turns
        self._messages = messages

    async def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
        prepared: PreparedEditorChatRequest,
        decision: ChatFailoverDecision,
        template_id: str,
    ) -> AsyncIterator[EditorChatStreamEvent]:
        request = prepared.request
        system_prompt = prepared.system_prompt
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
                if len(content) - last_flushed_len < STREAM_FLUSH_MIN_CHARS and (
                    time.monotonic() - last_flush_at < STREAM_FLUSH_MAX_INTERVAL_SECONDS
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
                self._providers.primary if provider_key == "primary" else self._providers.fallback
            )
            if provider is None:
                provider_key = "primary"
                provider = self._providers.primary

            if provider_key == "fallback":
                await self._failover.mark_fallback_used(user_id=actor.id, tool_id=command.tool_id)
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
            and (command.allow_remote_fallback or not self._providers.fallback_is_remote)
        ):
            provider_key = "fallback"
            provider = self._providers.fallback
            if provider is not None:
                await self._failover.mark_fallback_used(user_id=actor.id, tool_id=command.tool_id)
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
                    failure_outcome = "over_budget" if _is_context_window_error(exc) else "error"
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
            and not command.allow_remote_fallback
        ):
            await finalize_turn(
                status="failed",
                failure_outcome=REMOTE_FALLBACK_REQUIRED_CODE,
                provider=provider_key,
            )
            yield EditorChatDoneEvent(
                data=EditorChatDoneDisabledData(
                    message=REMOTE_FALLBACK_REQUIRED_MESSAGE,
                    code=REMOTE_FALLBACK_REQUIRED_CODE,
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
