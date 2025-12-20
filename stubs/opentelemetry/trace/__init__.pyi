from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import ContextManager, Protocol

AttributeValue = str | bool | int | float
Attributes = Mapping[str, AttributeValue]

class SpanContext(Protocol):
    is_valid: bool
    trace_id: int
    span_id: int

class StatusCode(enum.Enum):
    OK = 1
    ERROR = 2

class Status:
    status_code: StatusCode
    description: str | None

    def __init__(self, status_code: StatusCode, description: str | None = ...) -> None: ...

class Span(Protocol):
    def is_recording(self) -> bool: ...
    def get_span_context(self) -> SpanContext: ...
    def set_attribute(self, key: str, value: AttributeValue) -> None: ...
    def add_event(self, name: str, attributes: Attributes | None = ...) -> None: ...
    def record_exception(self, exception: BaseException) -> None: ...
    def set_status(self, status: Status) -> None: ...

class Tracer(Protocol):
    def start_as_current_span(
        self,
        name: str,
        context: object | None = ...,
        kind: object | None = ...,
        attributes: Attributes | None = ...,
    ) -> ContextManager[Span]: ...

    def start_span(
        self,
        name: str,
        context: object | None = ...,
        kind: object | None = ...,
        attributes: Attributes | None = ...,
    ) -> Span: ...

def get_current_span() -> Span: ...
def get_tracer(instrumenting_module_name: str) -> Tracer: ...
def set_tracer_provider(tracer_provider: object) -> None: ...
