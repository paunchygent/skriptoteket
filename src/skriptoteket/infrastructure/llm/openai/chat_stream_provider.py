"""Streaming editor chat through the LLM provider door.

Purpose:
    Stream one OpenAI Responses answer for an editor chat turn through
    HuleEdu's LLM provider door for the teacher's ``AiDoorCaller``
    (TASK-SKRIPT-41-01-02) and yield its text deltas.

Relationships:
    Implements ``protocols.llm.ChatStreamProviderProtocol``. A daily-limit
    refusal raises ``AiDailyLimitReached`` and a busy door ``AiDoorBusy`` before
    the first delta; every other
    failure raises ``EditorLlmProviderError``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.door_replies import (
    failure_for_status,
    invalid_response,
)
from skriptoteket.infrastructure.llm.openai.parsing import extract_response_stream_delta
from skriptoteket.infrastructure.llm.openai.payloads import build_responses_payload
from skriptoteket.protocols.llm import (
    ChatStreamProviderProtocol,
    LLMChatRequest,
)
from skriptoteket.protocols.llm.common import EditorLlmProviderError
from skriptoteket.protocols.llm_door import (
    DoorOperation,
    DoorRequestFailed,
    DoorTimeout,
    LlmDoorClientProtocol,
)


class OpenAIChatStreamProvider(ChatStreamProviderProtocol):
    def __init__(self, *, settings: Settings, door: LlmDoorClientProtocol) -> None:
        self._model = settings.LLM_CHAT_MODEL.strip()
        self._reasoning_effort = settings.LLM_CHAT_REASONING_EFFORT
        self._text_verbosity = settings.LLM_CHAT_TEXT_VERBOSITY
        self._max_tokens = settings.LLM_CHAT_MAX_TOKENS
        self._timeout_seconds = settings.LLM_CHAT_TIMEOUT_SECONDS
        self._door = door

    async def stream_chat(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
        caller: AiDoorCaller,
    ) -> AsyncIterator[str]:
        payload = build_responses_payload(
            model=self._model,
            messages=[
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            instructions=system_prompt,
            max_tokens=self._max_tokens,
            reasoning_effort=self._reasoning_effort,
            text_verbosity=self._text_verbosity,
            stream=True,
        )

        try:
            async with self._door.stream(
                operation=DoorOperation.RESPONSES,
                payload=payload,
                caller=caller,
                timeout_seconds=self._timeout_seconds,
            ) as door_stream:
                if not door_stream.is_success:
                    raise failure_for_status(
                        status_code=door_stream.status_code,
                        body=door_stream.body,
                    )
                event_type: str | None = None
                async for line in door_stream.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(chunk, dict):
                        continue
                    if "error" in chunk:
                        raise invalid_response(detail=data)

                    delta, done = extract_response_stream_delta(chunk, event_type=event_type)
                    if delta:
                        yield delta
                    if done:
                        break
        except DoorTimeout as exc:
            raise EditorLlmProviderError(kind="timeout") from exc
        except DoorRequestFailed as exc:
            raise EditorLlmProviderError(kind="request_failed") from exc
