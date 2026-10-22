"""Editor chat ops (edit operations) through the LLM provider door.

Purpose:
    Send one OpenAI Responses body with the patch-only structured output
    format for an editor chat-ops request through HuleEdu's LLM provider door
    for the teacher's ``AiDoorCaller`` (TASK-SKRIPT-41-01-02).

Relationships:
    Implements ``protocols.llm.ChatOpsProviderProtocol``. Failures raise
    ``EditorLlmProviderError``; ``AiDailyLimitReached`` propagates.
"""

from __future__ import annotations

import structlog

from skriptoteket.config import Settings
from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.infrastructure.llm.openai.door_replies import (
    invalid_response,
    send_responses_call,
)
from skriptoteket.infrastructure.llm.openai.edit_ops_text_format import (
    EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT,
)
from skriptoteket.infrastructure.llm.openai.parsing import extract_response_output_text
from skriptoteket.infrastructure.llm.openai.payloads import build_responses_payload
from skriptoteket.protocols.llm import (
    ChatOpsProviderProtocol,
    LLMChatOpsResponse,
    LLMChatRequest,
)
from skriptoteket.protocols.llm_door import LlmDoorClientProtocol


class OpenAIChatOpsProvider(ChatOpsProviderProtocol):
    def __init__(self, *, settings: Settings, door: LlmDoorClientProtocol) -> None:
        self._environment = settings.ENVIRONMENT
        self._model = settings.LLM_CHAT_OPS_MODEL.strip()
        self._reasoning_effort = settings.LLM_CHAT_OPS_REASONING_EFFORT
        self._text_verbosity = settings.LLM_CHAT_OPS_TEXT_VERBOSITY
        self._max_tokens = settings.LLM_CHAT_OPS_MAX_TOKENS
        self._timeout_seconds = settings.LLM_CHAT_OPS_TIMEOUT_SECONDS
        self._door = door

    async def complete_chat_ops(
        self,
        *,
        request: LLMChatRequest,
        system_prompt: str,
        caller: AiDoorCaller,
    ) -> LLMChatOpsResponse:
        payload = build_responses_payload(
            model=self._model,
            messages=[
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            instructions=system_prompt,
            max_tokens=self._max_tokens,
            reasoning_effort=self._reasoning_effort,
            text_verbosity=self._text_verbosity,
            stream=False,
            text_format=EDIT_OPS_PATCH_ONLY_RESPONSES_TEXT_FORMAT,
        )
        if self._environment != "production":
            structlog.get_logger(__name__).info(
                "chat_ops_structured_output",
                model=self._model,
                text_format="text" in payload,
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
        return LLMChatOpsResponse(
            content=content,
            finish_reason=finish_reason,
            raw_payload=dict(response_payload),
        )
