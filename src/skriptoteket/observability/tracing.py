"""OpenTelemetry tracing singleton for Skriptoteket.

Follows HuleEdu observability spec with W3C Trace Context propagation.
Tracing is opt-in: disabled when OTEL_TRACING_ENABLED is False.

API matches huleedu_service_libs.observability.tracing for future compatibility.

Usage:
    from skriptoteket.observability.tracing import init_tracing, get_tracer, trace_operation

    # Initialize once at app startup
    tracer = init_tracing("skriptoteket")

    # Use in handlers/services
    tracer = get_tracer("skriptoteket")
    with trace_operation(tracer, "my_operation", {"key": "value"}) as span:
        span.add_event("milestone", {"detail": "info"})
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from opentelemetry.trace import Span, Tracer

AttributeValue = str | bool | int | float
Attributes = Mapping[str, AttributeValue]

# Module-level singleton
_tracer: Tracer | None = None
_initialized: bool = False


def init_tracing(service_name: str) -> Tracer:
    """Initialize OpenTelemetry tracing with OTLP export.

    Matches HuleEdu API: reads SERVICE_VERSION, ENVIRONMENT, OTEL_EXPORTER_OTLP_ENDPOINT
    from environment variables.

    Called once at application startup. Returns a Tracer instance.
    Thread-safe: safe to call multiple times (subsequent calls return cached tracer).

    Args:
        service_name: The name of the service (e.g., "skriptoteket")

    Returns:
        A Tracer instance (or NoOpTracer if tracing is disabled)
    """
    global _tracer, _initialized

    if _initialized and _tracer is not None:
        return _tracer

    # Check if tracing is enabled (explicit opt-in for monolith)
    tracing_enabled = os.getenv("OTEL_TRACING_ENABLED", "false").lower() in ("true", "1", "yes")
    if not tracing_enabled:
        _initialized = True
        _tracer = _get_noop_tracer()
        return _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        # Read config from environment (HuleEdu pattern)
        service_version = os.getenv("SERVICE_VERSION", os.getenv("APP_VERSION", "1.0.0"))
        environment = os.getenv("ENVIRONMENT", "development")
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
            "service.namespace": "huleedu",
        })

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # W3C Trace Context for cross-service propagation
        set_global_textmap(TraceContextTextMapPropagator())

        _tracer = trace.get_tracer(service_name)
        _initialized = True
        return _tracer

    except ImportError:
        # OpenTelemetry not installed - return no-op tracer
        _initialized = True
        _tracer = _get_noop_tracer()
        return _tracer


def get_tracer(service_name: str) -> Tracer:
    """Get the singleton tracer instance.

    Matches HuleEdu API signature.

    Returns NoOpTracer if:
    - Tracing is not enabled (OTEL_TRACING_ENABLED=false)
    - init_tracing() was not called
    - OpenTelemetry packages are not installed

    Args:
        service_name: The name of the service (for compatibility, currently ignored
                      as we use singleton pattern)

    Returns:
        The cached Tracer or NoOpTracer
    """
    global _tracer
    if _tracer is not None:
        return _tracer
    return _get_noop_tracer()


def get_current_trace_id() -> str | None:
    """Extract 32-char hex trace ID from current span.

    Matches HuleEdu API. Useful for debugging and log correlation.

    Returns:
        32-character hex trace ID, or None if no active span
    """
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            if ctx.is_valid:
                return format(ctx.trace_id, "032x")
    except ImportError:
        pass
    return None


def _get_noop_tracer() -> Tracer:
    """Return a no-op tracer for when tracing is disabled."""
    try:
        from opentelemetry import trace

        return trace.get_tracer("noop")
    except ImportError:
        # Return a minimal stub that satisfies the Tracer interface
        return _NoOpTracerStub()


class _NoOpSpanStub:
    """Minimal stub span for when OpenTelemetry is not installed."""

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        pass

    def add_event(self, name: str, attributes: Attributes | None = None) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def set_status(self, status: object) -> None:
        pass

    def is_recording(self) -> bool:
        return False

    def get_span_context(self) -> _NoOpSpanContextStub:
        return _NoOpSpanContextStub()

    def end(self) -> None:
        pass

    def __enter__(self) -> _NoOpSpanStub:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        pass


class _NoOpSpanContextStub:
    """Minimal stub span context for when OpenTelemetry is not installed."""

    is_valid: bool = False
    trace_id: int = 0
    span_id: int = 0


class _NoOpTracerStub:
    """Minimal stub tracer for when OpenTelemetry is not installed."""

    def start_as_current_span(
        self,
        name: str,
        context: object | None = None,
        kind: object | None = None,
        attributes: Attributes | None = None,
    ) -> _NoOpSpanStub:
        return _NoOpSpanStub()

    def start_span(
        self,
        name: str,
        context: object | None = None,
        kind: object | None = None,
        attributes: Attributes | None = None,
    ) -> _NoOpSpanStub:
        return _NoOpSpanStub()


@contextmanager
def trace_operation(
    tracer: Tracer,
    operation_name: str,
    attributes: Mapping[str, str] | None = None,
) -> Iterator[Span]:
    """Context manager for tracing operations with automatic error handling.

    Matches HuleEdu API.

    Usage:
        with trace_operation(tracer, "process_tool", {"tool_id": str(tool_id)}) as span:
            result = await do_work()
            span.set_attribute("result_status", result.status)

    Exceptions are automatically recorded in the span with ERROR status.

    Args:
        tracer: The tracer instance from get_tracer()
        operation_name: Name of the span
        attributes: Optional initial attributes to set on the span

    Yields:
        The active span for adding events and attributes
    """
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            try:
                from opentelemetry.trace import Status, StatusCode

                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            except ImportError:
                pass
            raise
