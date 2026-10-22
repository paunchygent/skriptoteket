"""Inline completion through the LLM provider door.

Purpose:
    Send one OpenAI Responses body for an editor inline completion through
    HuleEdu's LLM provider door for the teacher's ``AiDoorCaller``
    (TASK-SKRIPT-41-01-02). The door owns the key, the user id and the
    metering; this provider owns the body and parses the relayed answer.

Relationships:
    Implements ``protocols.llm.InlineCompletionProviderProtocol``. Failures
    raise ``EditorLlmProviderError``; ``AiDailyLimitReached`` propagates.
"""

from __future__ import annotations

import structlog

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.door_replies import (
    invalid_response,
    send_responses_call,
)
from skriptoteket.infrastructure.llm.openai.inline_completion_prompt import (
    build_delimited_inline_completion_prompt,
)
from skriptoteket.infrastructure.llm.openai.parsing import extract_response_output_text
from skriptoteket.infrastructure.llm.openai.payloads import build_responses_payload
from skriptoteket.protocols.llm import (
    InlineCompletionProviderProtocol,
    LLMCompletionRequest,
    LLMCompletionResponse,
)
from skriptoteket.protocols.llm_door import LlmDoorClientProtocol


class OpenAIInlineCompletionProvider(InlineCompletionProviderProtocol):
    def __init__(self, *, settings: Settings, door: LlmDoorClientProtocol) -> None:
        self._environment = settings.ENVIRONMENT
        self._model = settings.LLM_COMPLETION_MODEL.strip()
        self._reasoning_effort = settings.LLM_COMPLETION_REASONING_EFFORT
        self._text_verbosity = settings.LLM_COMPLETION_TEXT_VERBOSITY
        self._max_tokens = settings.LLM_COMPLETION_MAX_TOKENS
        self._timeout_seconds = settings.LLM_COMPLETION_TIMEOUT_SECONDS
        self._door = door

    async def complete_inline(
        self,
        *,
        request: LLMCompletionRequest,
        system_prompt: str,
        caller: AiDoorCaller,
    ) -> LLMCompletionResponse:
        user_prompt = build_delimited_inline_completion_prompt(
            prefix=request.prefix,
            suffix=request.suffix,
            active_file=request.active_file,
        )
        payload = build_responses_payload(
            model=self._model,
            messages=[{"role": "user", "content": user_prompt}],
            instructions=system_prompt,
            max_tokens=self._max_tokens,
            reasoning_effort=self._reasoning_effort,
            text_verbosity=self._text_verbosity,
            stream=False,
            store=False,
            truncation="auto",
        )

        if self._environment != "production":
            structlog.get_logger(__name__).info(
                "inline_completion_payload_shape",
                model=self._model,
                has_reasoning="reasoning" in payload,
                has_text="text" in payload,
                store=payload.get("store"),
                truncation=payload.get("truncation"),
            )

        response_payload = await send_responses_call(
            door=self._door,
            payload=payload,
            caller=caller,
            timeout_seconds=self._timeout_seconds,
        )
        try:
            content, finish_reason = extract_response_output_text(response_payload)
        except ValueError as exc:
            raise invalid_response(detail=str(exc)) from exc
        return LLMCompletionResponse(completion=content, finish_reason=finish_reason)
