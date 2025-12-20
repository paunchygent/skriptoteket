from __future__ import annotations

from opentelemetry.sdk.resources import Resource

class TracerProvider:
    def __init__(self, *, resource: Resource) -> None: ...
    def add_span_processor(self, processor: object) -> None: ...
