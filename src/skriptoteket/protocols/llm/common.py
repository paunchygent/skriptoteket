"""Shared literal types for LLM protocols."""

from __future__ import annotations

from typing import Literal

SystemMessageVariant = Literal["info", "warning"]
VirtualFileId = Literal[
    "tool.py",
    "entrypoint.txt",
    "settings_schema.json",
    "input_schema.json",
    "usage_instructions.md",
]

EditorLlmFailureKind = Literal[
    "timeout",
    "request_failed",
    "context_window_exceeded",
    "http_status",
    "invalid_response",
]


class EditorLlmProviderError(Exception):
    """An editor AI call through the LLM provider door failed.

    A daily-limit refusal is never this error; it is ``AiDailyLimitReached``.
    ``timeout`` and ``request_failed`` come from the door call; an unsuccessful
    relayed answer is ``context_window_exceeded`` when OpenAI's error code is
    ``context_length_exceeded``, otherwise ``http_status`` with its
    ``status_code`` (a door capacity 429 included); an answer that cannot be
    parsed, or a stream error event, is ``invalid_response``. ``detail`` holds
    at most 2,000 characters of the error body for logs and captures.
    """

    def __init__(
        self,
        *,
        kind: EditorLlmFailureKind,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        super().__init__(f"Editor AI call failed: {kind}")
        self.kind = kind
        self.status_code = status_code
        self.detail = detail
