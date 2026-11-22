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
from typing import TypedDict

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


class UsageDetails(TypedDict, total=False):
    cached_tokens: JsonValue
    cache_write_tokens: JsonValue
    reasoning_tokens: JsonValue


class UsageInfo(TypedDict, total=False):
    input_tokens: JsonValue
    input_tokens_details: UsageDetails
    output_tokens: JsonValue
    output_tokens_details: JsonValue


def usage_details(value: JsonValue | None, *, tolerate_non_object: bool) -> UsageDetails:
    """Token-count details; a falsy non-object reads as empty like the old ``or {}``."""
    if not isinstance(value, dict):
        if value and not tolerate_non_object:
            raise TypeError("usage token details must be a JSON object")
        return {}
    details: UsageDetails = {}
    if "cached_tokens" in value:
        details["cached_tokens"] = value["cached_tokens"]
    if "cache_write_tokens" in value:
        details["cache_write_tokens"] = value["cache_write_tokens"]
    if "reasoning_tokens" in value:
        details["reasoning_tokens"] = value["reasoning_tokens"]
    return details


def _usage_info(value: JsonValue | None) -> UsageInfo:
    info: UsageInfo = {}
    if not isinstance(value, dict):
        return info
    if "input_tokens" in value:
        info["input_tokens"] = value["input_tokens"]
    if "output_tokens" in value:
        info["output_tokens"] = value["output_tokens"]
    if "input_tokens_details" in value:
        info["input_tokens_details"] = usage_details(
            value["input_tokens_details"], tolerate_non_object=True
        )
    if "output_tokens_details" in value:
        info["output_tokens_details"] = value["output_tokens_details"]
    return info


def _usage_object(body: JsonValue) -> dict[str, JsonValue]:
    """The usage object verbatim for evidence files, or empty when absent."""
    if not isinstance(body, dict):
        return {}
    usage = body.get("usage")
    return usage if isinstance(usage, dict) else {}


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
        """The provider's usage object as received; evidence files keep it whole."""
        return _usage_object(self.body)

    @property
    def usage_info(self) -> UsageInfo:
        """The usage fields the cost and summary arithmetic reads."""
        return _usage_info(self.usage)

    def cost_usd(self) -> float | None:
        usage = self.usage_info
        input_tokens = usage.get("input_tokens")
        if not isinstance(input_tokens, int):
            return None
        if self.endpoint == "decisions":
            return input_tokens * _DECISIONS_INPUT / 1_000_000
        detail_map = usage.get("input_tokens_details") or {}
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


def json_int(value: JsonValue | None, field_name: str) -> int:
    """A numeric JSON field coerced with ``int()``; a falsy value counts as zero."""
    if not value:
        return 0
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"{field_name} must be a JSON number or numeric string")
    return int(value)


def json_float(value: JsonValue, field_name: str) -> float:
    """A Decisions answer field passed through ``float()``: a number or numeric string."""
    if not isinstance(value, (int, float, str)):
        raise TypeError(f"{field_name} must be a JSON number or numeric string")
    return float(value)


class ProbabilityEntry(TypedDict, total=False):
    probability: float
    value: JsonValue


class DecisionAnswer(TypedDict, total=False):
    """One Decisions answer object narrowed to the fields the evaluators read."""

    name: str
    type: str
    choice: JsonValue
    score: str | float
    probability: float
    probabilities: list[ProbabilityEntry]


def _probability_entries(value: JsonValue) -> list[ProbabilityEntry]:
    if not isinstance(value, list):
        raise TypeError("decisions answer probabilities must be a JSON array")
    entries: list[ProbabilityEntry] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise TypeError("decisions answer probability entries must be JSON objects")
        probability = entry.get("probability")
        if not isinstance(probability, (int, float)):
            raise TypeError("decisions answer probability entries need a numeric probability")
        narrowed: ProbabilityEntry = {"probability": probability}
        if "value" in entry:
            narrowed["value"] = entry["value"]
        entries.append(narrowed)
    return entries


def decision_answer(value: JsonValue) -> DecisionAnswer | None:
    """A Decisions answer object narrowed field by field; None when it is not an object."""
    if not isinstance(value, dict):
        return None
    answer: DecisionAnswer = {}
    name = value.get("name")
    if isinstance(name, str):
        answer["name"] = name
    answer_type = value.get("type")
    if isinstance(answer_type, str):
        answer["type"] = answer_type
    if "choice" in value:
        answer["choice"] = value["choice"]
    if "score" in value:
        score = value["score"]
        if not isinstance(score, (int, float, str)):
            raise TypeError("decisions answer score must be a number or numeric string")
        answer["score"] = score
    if "probability" in value:
        probability = value["probability"]
        if not isinstance(probability, (int, float)):
            raise TypeError("decisions answer probability must be a JSON number")
        answer["probability"] = probability
    if "probabilities" in value:
        answer["probabilities"] = _probability_entries(value["probabilities"])
    return answer


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


class OutputPart(TypedDict, total=False):
    type: str
    text: str


class OutputItem(TypedDict, total=False):
    content: list[OutputPart]


def _output_part(value: JsonValue) -> OutputPart | None:
    if not isinstance(value, dict):
        return None
    part: OutputPart = {}
    part_type = value.get("type")
    if isinstance(part_type, str):
        part["type"] = part_type
    text = value.get("text")
    if isinstance(text, str):
        part["text"] = text
    return part


def _output_item(value: JsonValue) -> OutputItem | None:
    if not isinstance(value, dict):
        return None
    item: OutputItem = {}
    content = value.get("content")
    if isinstance(content, list):
        item["content"] = [part for part in (_output_part(p) for p in content) if part is not None]
    return item


def _output_items(body: JsonValue) -> list[OutputItem] | None:
    """The reply's output items, or None when the body has no output array."""
    if not isinstance(body, dict):
        return None
    output = body.get("output")
    if not isinstance(output, list):
        return None
    return [item for item in (_output_item(value) for value in output) if item is not None]


def responses_output_json(record: CallRecord) -> JsonValue | None:
    """Parse the structured output text of a completed Responses call."""
    items = _output_items(record.body)
    if items is None:
        return None
    for item in items:
        content = item.get("content")
        if content is None:
            continue
        for part in content:
            if part.get("type") == "output_text":
                text = part.get("text")
                return json.loads(text) if text is not None else None
    return None


def listed_answers(body: JsonValue) -> list[JsonValue]:
    """The reply's ``answers`` array, or empty when the body has none."""
    if not isinstance(body, dict):
        return []
    listed = body.get("answers")
    return listed if isinstance(listed, list) else []


def decision_answers(record: CallRecord) -> dict[str, dict[str, JsonValue]]:
    """The reply's answer objects by name, each kept whole for the saved evidence."""
    found: dict[str, dict[str, JsonValue]] = {}
    for answer in listed_answers(record.body):
        if not isinstance(answer, dict):
            continue
        name = answer.get("name")
        if isinstance(name, str):
            found[name] = answer
    return found


def answer_map(value: JsonValue) -> dict[str, DecisionAnswer]:
    """A saved or live Decisions answer map narrowed answer by answer."""
    if not isinstance(value, dict):
        raise TypeError("decisions answers must be a JSON object")
    answers: dict[str, DecisionAnswer] = {}
    for name, raw in value.items():
        narrowed = decision_answer(raw)
        if narrowed is None:
            raise TypeError(f"decisions answer {name} must be a JSON object")
        answers[name] = narrowed
    return answers
