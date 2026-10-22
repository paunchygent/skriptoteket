"""Responses SSE text observation and authoritative terminal-payload collection.

No structured-content or application identity validation belongs here. The final
response is parsed by the ordinary structured provider after the door scope ends.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from pydantic import JsonValue

from skriptoteket.protocols.exam_answer_key import StructuredLLMTextObserver


class ResponseStreamError(ValueError):
    """The provider stream did not produce an ordinary terminal response."""


class ResponseStreamRefusal(ResponseStreamError):
    """The provider refused the structured request."""


async def _events(lines: AsyncIterator[str]) -> AsyncIterator[tuple[str, str]]:
    event_type = ""
    data: list[str] = []
    async for line in lines:
        if not line:
            if data:
                yield event_type, "\n".join(data)
            event_type = ""
            data = []
            continue
        if line.startswith("event:"):
            event_type = line[6:].lstrip(" ")
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    # An unframed final event is not dispatched by SSE.


async def observe_response_stream(
    *, lines: AsyncIterator[str], on_text: StructuredLLMTextObserver
) -> dict[str, JsonValue]:
    terminal: dict[str, JsonValue] | None = None
    refused = False
    failure: ResponseStreamError | None = None
    async for event_type, data in _events(lines):
        if data == "[DONE]":
            continue
        try:
            event: JsonValue = json.loads(data)
        except ValueError:
            failure = ResponseStreamError("Structured provider stream event was not valid JSON.")
            continue
        if not isinstance(event, dict):
            failure = ResponseStreamError("Structured provider stream event was not an object.")
            continue
        kind = event.get("type", event_type)
        if kind == "response.output_text.delta":
            delta = event.get("delta")
            if not isinstance(delta, str):
                failure = ResponseStreamError("Structured provider stream delta was not text.")
            elif delta and failure is None:
                await on_text(delta)
        elif kind in ("response.refusal.delta", "response.refusal.done"):
            refused = True
        elif kind in ("error", "response.failed"):
            failure = ResponseStreamError("Structured provider reported a stream failure.")
        elif kind in ("response.completed", "response.incomplete"):
            response = event.get("response")
            if not isinstance(response, dict):
                failure = ResponseStreamError("Structured provider terminal event had no response.")
                continue
            expected_status = "completed" if kind == "response.completed" else "incomplete"
            if response.get("status") != expected_status:
                failure = ResponseStreamError(
                    "Structured provider terminal event status did not match."
                )
                continue
            terminal = response
        # Do not stop at a provider terminal event: the door settles after it.
    if failure is not None:
        raise failure
    if refused:
        raise ResponseStreamRefusal("Structured provider returned a refusal.")
    if terminal is None:
        raise ResponseStreamError("Structured provider stream ended without a terminal response.")
    return terminal
