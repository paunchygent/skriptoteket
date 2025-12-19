from __future__ import annotations

from typing import Protocol

class SpanContext(Protocol):
    is_valid: bool
    trace_id: int
    span_id: int


class Span(Protocol):
    def is_recording(self) -> bool: ...
    def get_span_context(self) -> SpanContext: ...


def get_current_span() -> Span: ...

