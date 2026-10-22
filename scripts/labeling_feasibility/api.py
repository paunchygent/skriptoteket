"""Raw OpenAI Decisions and Responses calls relayed through the provider door.

The request bodies are unchanged OpenAI payloads; the door client owns the key,
the teacher's user id, the exempt flag and the paid-overage mode. Usage, timing
and limit headers are kept as with the direct calls.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pydantic import JsonValue

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
    body: JsonValue
    request_summary: dict[str, JsonValue] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status_code == 200 and isinstance(self.body, dict)

    @property
    def usage(self) -> dict[str, JsonValue]:
        if not isinstance(self.body, dict):
            return {}
        usage = self.body.get("usage")
        return usage if isinstance(usage, dict) else {}

    def cost_usd(self) -> float | None:
        usage = self.usage
        input_tokens = usage.get("input_tokens")
        if not isinstance(input_tokens, int):
            return None
        if self.endpoint == "decisions":
            return input_tokens * _DECISIONS_INPUT / 1_000_000
        details = usage.get("input_tokens_details")
        detail_map = details if isinstance(details, dict) else {}
        cached = _count(detail_map.get("cached_tokens"))
        written = _count(detail_map.get("cache_write_tokens"))
        uncached = input_tokens - cached - written
        output = _count(usage.get("output_tokens"))
        return (
            uncached * _RESPONSES_UNCACHED
            + cached * _RESPONSES_CACHED
            + written * _RESPONSES_CACHE_WRITE
            + output * _RESPONSES_OUTPUT
        ) / 1_000_000

    def to_json(self) -> dict[str, JsonValue]:
        headers: dict[str, JsonValue] = {name: value for name, value in self.headers.items()}
        summary: dict[str, JsonValue] = {
            name: value for name, value in self.request_summary.items()
        }
        return {
            "endpoint": self.endpoint,
            "label": self.label,
            "status_code": self.status_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "headers": headers,
            "usage": self.usage,
            "cost_usd": self.cost_usd(),
            "request_summary": summary,
            "body": self.body,
        }


def _count(value: JsonValue | None) -> int:
    """A token count that is missing or malformed counts as zero in this estimate."""

    return value if isinstance(value, int) else 0


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
        payload: Mapping[str, JsonValue],
        summary: Mapping[str, JsonValue],
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
            body: JsonValue = json.loads(reply.body)
        except json.JSONDecodeError:
            body = reply.body.decode("utf-8", errors="replace")
        headers: dict[str, str] = {
            name: reply.headers[name] for name in _KEPT_HEADERS if name in reply.headers
        }
        return CallRecord(
            endpoint, label, reply.status_code, duration, headers, body, dict(summary)
        )

    async def decisions(
        self,
        *,
        label: str,
        input_value: str | Sequence[Mapping[str, JsonValue]],
        questions: Sequence[Mapping[str, JsonValue]],
    ) -> CallRecord:
        question_values: list[JsonValue] = [dict(question) for question in questions]
        if isinstance(input_value, str):
            input_json: JsonValue = input_value
        else:
            input_json = [dict(item) for item in input_value]
        payload: dict[str, JsonValue] = {
            "model": DECISIONS_MODEL,
            "input": input_json,
            "questions": question_values,
        }
        summary: dict[str, JsonValue] = {
            "questions": len(question_values),
            "input_chars": len(json.dumps(input_value)),
        }
        return await self._post(DoorOperation.DECISIONS, "decisions", label, payload, summary)

    async def responses(
        self,
        *,
        label: str,
        model: str,
        instructions: str,
        user_text: str,
        schema_name: str,
        schema: Mapping[str, JsonValue],
        reasoning_effort: str,
        max_output_tokens: int,
    ) -> CallRecord:
        schema_json: dict[str, JsonValue] = dict(schema)
        payload: dict[str, JsonValue] = {
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
                    "schema": schema_json,
                },
                "verbosity": "low",
            },
        }
        summary: dict[str, JsonValue] = {
            "model": model,
            "effort": reasoning_effort,
            "input_chars": len(user_text),
        }
        return await self._post(DoorOperation.RESPONSES, "responses", label, payload, summary)


def responses_output_json(record: CallRecord) -> JsonValue | None:
    """Parse the structured output text of a completed Responses call."""
    body = record.body
    if not isinstance(body, dict):
        return None
    output = body.get("output")
    if not isinstance(output, list):
        return None
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text":
                text = part.get("text")
                return json.loads(text) if isinstance(text, str) else None
    return None


def decision_answers(record: CallRecord) -> dict[str, dict[str, JsonValue]]:
    body = record.body
    if not isinstance(body, dict):
        return {}
    listed = body.get("answers")
    if not isinstance(listed, list):
        return {}
    found: dict[str, dict[str, JsonValue]] = {}
    for answer in listed:
        if not isinstance(answer, dict):
            continue
        name = answer.get("name")
        if isinstance(name, str):
            found[name] = answer
    return found
