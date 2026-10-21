"""Raw OpenAI Decisions and Responses calls relayed through the provider door.

The request bodies are unchanged OpenAI payloads; the door client owns the key,
the teacher's user id, the exempt flag and the paid-overage mode. Usage, timing
and limit headers are kept as with the direct calls.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from skriptoteket.domain.llm_door import AiDoorCaller
from skriptoteket.protocols.llm_door import DoorOperation, LlmDoorClientProtocol

DECISIONS_MODEL = "gpt-6-luna"
_KEPT_HEADERS = (
    "x-request-id",
    "openai-processing-ms",
    "openai-model",
    "retry-after",
    "x-ratelimit-limit-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-requests",
    "x-ratelimit-reset-tokens",
    "x-ratelimit-limit-project-tokens",
    "x-ratelimit-remaining-project-tokens",
    "x-ratelimit-reset-project-tokens",
)

# Published gpt-6-luna standard prices, USD per million tokens (read 2026-10-11).
_RESPONSES_UNCACHED = 0.10
_RESPONSES_CACHED = 0.01
_RESPONSES_CACHE_WRITE = 0.125
_RESPONSES_OUTPUT = 0.50
_DECISIONS_INPUT = 0.10


@dataclass
class CallRecord:
    endpoint: str
    label: str
    status_code: int
    duration_seconds: float
    headers: dict[str, str]
    body: Any
    request_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status_code == 200 and isinstance(self.body, dict)

    @property
    def usage(self) -> dict[str, Any]:
        usage = self.body.get("usage") if isinstance(self.body, dict) else None
        return usage if isinstance(usage, dict) else {}

    def cost_usd(self) -> float | None:
        usage = self.usage
        input_tokens = usage.get("input_tokens")
        if not isinstance(input_tokens, int):
            return None
        if self.endpoint == "decisions":
            return input_tokens * _DECISIONS_INPUT / 1_000_000
        details = usage.get("input_tokens_details") or {}
        cached = int(details.get("cached_tokens") or 0)
        written = int(details.get("cache_write_tokens") or 0)
        uncached = input_tokens - cached - written
        output = int(usage.get("output_tokens") or 0)
        return (
            uncached * _RESPONSES_UNCACHED
            + cached * _RESPONSES_CACHED
            + written * _RESPONSES_CACHE_WRITE
            + output * _RESPONSES_OUTPUT
        ) / 1_000_000

    def to_json(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "label": self.label,
            "status_code": self.status_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "headers": self.headers,
            "usage": self.usage,
            "cost_usd": self.cost_usd(),
            "request_summary": self.request_summary,
            "body": self.body,
        }


class OpenAIClient:
    """OpenAI-dialect Decisions/Responses calls sent through the provider door."""

    def __init__(
        self, *, door: LlmDoorClientProtocol, caller: AiDoorCaller, timeout: float
    ) -> None:
        self._door = door
        self._caller = caller
        self._timeout = timeout

    async def _post(
        self,
        operation: DoorOperation,
        endpoint: str,
        label: str,
        payload: dict[str, Any],
        summary: dict[str, Any],
    ) -> CallRecord:
        started = time.perf_counter()
        reply = await self._door.send(
            operation=operation,
            payload=payload,
            caller=self._caller,
            timeout_seconds=self._timeout,
        )
        duration = time.perf_counter() - started
        try:
            body: Any = json.loads(reply.body)
        except json.JSONDecodeError:
            body = reply.body.decode("utf-8", errors="replace")
        headers = {name: reply.headers[name] for name in _KEPT_HEADERS if name in reply.headers}
        return CallRecord(endpoint, label, reply.status_code, duration, headers, body, summary)

    async def decisions(
        self,
        *,
        label: str,
        input_value: str | list[dict[str, Any]],
        questions: list[dict[str, Any]],
    ) -> CallRecord:
        payload = {"model": DECISIONS_MODEL, "input": input_value, "questions": questions}
        summary = {"questions": len(questions), "input_chars": len(json.dumps(input_value))}
        return await self._post(DoorOperation.DECISIONS, "decisions", label, payload, summary)

    async def responses(
        self,
        *,
        label: str,
        model: str,
        instructions: str,
        user_text: str,
        schema_name: str,
        schema: dict[str, Any],
        reasoning_effort: str,
        max_output_tokens: int,
    ) -> CallRecord:
        payload = {
            "model": model,
            "instructions": instructions,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_text}],
                }
            ],
            "stream": False,
            "store": False,
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": reasoning_effort},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
                "verbosity": "low",
            },
        }
        summary = {"model": model, "effort": reasoning_effort, "input_chars": len(user_text)}
        return await self._post(DoorOperation.RESPONSES, "responses", label, payload, summary)


def responses_output_json(record: CallRecord) -> Any:
    """Parse the structured output text of a completed Responses call."""
    body = record.body
    if not isinstance(body, dict):
        return None
    for item in body.get("output") or []:
        for part in item.get("content") or []:
            if part.get("type") == "output_text":
                return json.loads(part["text"])
    return None


def decision_answers(record: CallRecord) -> dict[str, dict[str, Any]]:
    body = record.body
    if not isinstance(body, dict):
        return {}
    return {answer["name"]: answer for answer in body.get("answers") or [] if "name" in answer}
