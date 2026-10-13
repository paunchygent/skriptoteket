"""Raw OpenAI Decisions and Responses calls that keep usage, timing and limit headers."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

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
    def __init__(self, *, client: httpx.AsyncClient, base_url: str, api_key: str, timeout: float):
        self._client = client
        self._base_url = (
            base_url.rstrip("/")
            if base_url.rstrip("/").endswith("/v1")
            else f"{base_url.rstrip('/')}/v1"
        )
        self._api_key = api_key
        self._timeout = timeout

    async def _post(
        self, endpoint: str, label: str, payload: dict[str, Any], summary: dict[str, Any]
    ) -> CallRecord:
        started = time.perf_counter()
        response = await self._client.post(
            f"{self._base_url}/{endpoint}",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        )
        duration = time.perf_counter() - started
        try:
            body: Any = response.json()
        except json.JSONDecodeError:
            body = response.text
        headers = {
            name: response.headers[name] for name in _KEPT_HEADERS if name in response.headers
        }
        return CallRecord(endpoint, label, response.status_code, duration, headers, body, summary)

    async def decisions(
        self,
        *,
        label: str,
        input_value: str | list[dict[str, Any]],
        questions: list[dict[str, Any]],
    ) -> CallRecord:
        payload = {"model": DECISIONS_MODEL, "input": input_value, "questions": questions}
        summary = {"questions": len(questions), "input_chars": len(json.dumps(input_value))}
        return await self._post("decisions", label, payload, summary)

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
        return await self._post("responses", label, payload, summary)


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
