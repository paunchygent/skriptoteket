from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import aclosing
from typing import Literal

import structlog

from skriptoteket.application.editor.chat_shared import (
    CHAT_TURN_PROVIDER,
    DAILY_LIMIT_OUTCOME,
    DOOR_BUSY_OUTCOME,
    STREAM_FLUSH_MAX_INTERVAL_SECONDS,
    STREAM_FLUSH_MIN_CHARS,
)
from skriptoteket.application.editor.chat_stream.capture import capture_chat_request_context
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import (
    AiDailyLimitReached,
    AiDoorBusy,
    door_caller_for,
    door_refusal_error,
)
from skriptoteket.protocols.editor_chat import (
    EditorChatStreamOrchestratorProtocol,
    PreparedEditorChatRequest,
)
from skriptoteket.protocols.llm import (
    ChatStreamProviderProtocol,
    EditorChatCommand,
    EditorChatDeltaData,
    EditorChatDeltaEvent,
    EditorChatDoneEnabledData,
    EditorChatDoneEvent,
    EditorChatMetaData,
    EditorChatMetaEvent,
    EditorChatStreamEvent,
    EditorLlmProviderError,
)
from skriptoteket.protocols.llm_captures import LlmCaptureStoreProtocol
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

logger = structlog.get_logger(__name__)


def _failure_outcome(error: EditorLlmProviderError) -> str:
    if error.kind == "timeout":
        return "timeout"
    if error.kind == "context_window_exceeded":
        return "over_budget"
    return "error"


class EditorChatStreamOrchestrator(EditorChatStreamOrchestratorProtocol):
    def __init__(
        self,
        *,
        settings: Settings,
        capture_store: LlmCaptureStoreProtocol,
        provider: ChatStreamProviderProtocol,
        uow: UnitOfWorkProtocol,
        turns: ToolSessionTurnRepositoryProtocol,
        messages: ToolSessionMessageRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._capture_store = capture_store
        self._provider = provider
        self._uow = uow
        self._turns = turns
        self._messages = messages

    async def stream(
        self,
        *,
        actor: User,
        command: EditorChatCommand,
        prepared: PreparedEditorChatRequest,
        template_id: str,
    ) -> AsyncGenerator[EditorChatStreamEvent, None]:
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

        await capture_chat_request_context(
            settings=self._settings,
            capture_store=self._capture_store,
            template_id=template_id,
            actor=actor,
            command=command,
            request=request,
            capture_id=prepared.correlation_id,
        )

        start = time.perf_counter()
        output_chars = 0
        saw_delta = False
        assistant_chunks: list[str] = []
        failure_outcome: str | None = None
        failure_status_code: int | None = None
        door_refusal: AiDailyLimitReached | AiDoorBusy | None = None

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
                    provider=CHAT_TURN_PROVIDER,
                )

        meta_event = EditorChatMetaEvent(
            data=EditorChatMetaData(
                correlation_id=prepared.correlation_id,
                turn_id=prepared.turn_id,
                assistant_message_id=prepared.assistant_message_id,
            )
        )
        # The meta event waits for the provider's first answer: the door refuses a daily
        # limit, and a busy door refuses the stream, before that answer, and the refusal
        # must reach the web layer as an HTTP error before any event opens the SSE response.
        meta_sent = False

        try:
            async with aclosing(
                self._provider.stream_chat(
                    request=request,
                    system_prompt=system_prompt,
                    caller=door_caller_for(user=actor),
                )
            ) as deltas:
                async for delta in deltas:
                    if not meta_sent:
                        meta_sent = True
                        yield meta_event
                    if not delta:
                        continue
                    saw_delta = True
                    output_chars += len(delta)
                    assistant_chunks.append(delta)
                    await flush_assistant_content()
                    yield EditorChatDeltaEvent(data=EditorChatDeltaData(text=delta))
        except (asyncio.CancelledError, GeneratorExit):
            # A cancelled task or a consumer that closed this generator (a dropped
            # client): the provider stream is already closed; end the turn as cancelled.
            await finalize_turn(status="cancelled", failure_outcome="cancelled")
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
        except AiDailyLimitReached as exc:
            door_refusal = exc
            failure_outcome = DAILY_LIMIT_OUTCOME
        except AiDoorBusy as exc:
            door_refusal = exc
            failure_outcome = DOOR_BUSY_OUTCOME
        except EditorLlmProviderError as exc:
            failure_outcome = _failure_outcome(exc)
            failure_status_code = exc.status_code

        if failure_outcome is not None:
            await finalize_turn(status="failed", failure_outcome=failure_outcome)
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
            if door_refusal is not None and not meta_sent:
                raise door_refusal_error(door_refusal) from door_refusal
            if not meta_sent:
                yield meta_event
            yield EditorChatDoneEvent(data=EditorChatDoneEnabledData(reason="error"))
            return

        if not meta_sent:
            yield meta_event
        await finalize_turn(status="complete", failure_outcome=None)
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
