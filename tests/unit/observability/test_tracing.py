"""Unit tests for OpenTelemetry tracing module."""

from __future__ import annotations

import pytest

from skriptoteket.observability.tracing import (
    _NoOpSpanContextStub,
    _NoOpSpanStub,
    _NoOpTracerStub,
    get_tracer,
    trace_operation,
)


@pytest.mark.unit
class TestNoOpSpanStub:
    """Tests for the NoOp span stub."""

    def test_set_attribute_when_called_does_not_raise(self) -> None:
        span = _NoOpSpanStub()
        span.set_attribute("key", "value")

    def test_add_event_when_called_does_not_raise(self) -> None:
        span = _NoOpSpanStub()
        span.add_event("event_name")
        span.add_event("event_name", {"key": "value"})

    def test_record_exception_when_called_does_not_raise(self) -> None:
        span = _NoOpSpanStub()
        span.record_exception(ValueError("test"))

    def test_set_status_when_called_does_not_raise(self) -> None:
        span = _NoOpSpanStub()
        span.set_status(object())

    def test_is_recording_returns_false(self) -> None:
        span = _NoOpSpanStub()
        assert span.is_recording() is False

    def test_get_span_context_returns_invalid_context(self) -> None:
        span = _NoOpSpanStub()
        ctx = span.get_span_context()
        assert isinstance(ctx, _NoOpSpanContextStub)
        assert ctx.is_valid is False
        assert ctx.trace_id == 0
        assert ctx.span_id == 0

    def test_end_when_called_does_not_raise(self) -> None:
        span = _NoOpSpanStub()
        span.end()

    def test_context_manager_when_entered_returns_self(self) -> None:
        span = _NoOpSpanStub()
        with span as entered:
            assert entered is span


@pytest.mark.unit
class TestNoOpTracerStub:
    """Tests for the NoOp tracer stub."""

    def test_start_as_current_span_returns_span_stub(self) -> None:
        tracer = _NoOpTracerStub()
        span = tracer.start_as_current_span("test_span")
        assert isinstance(span, _NoOpSpanStub)

    def test_start_as_current_span_with_attributes_returns_span_stub(self) -> None:
        tracer = _NoOpTracerStub()
        span = tracer.start_as_current_span(
            "test_span",
            attributes={"key": "value"},
        )
        assert isinstance(span, _NoOpSpanStub)

    def test_start_span_returns_span_stub(self) -> None:
        tracer = _NoOpTracerStub()
        span = tracer.start_span("test_span")
        assert isinstance(span, _NoOpSpanStub)


@pytest.mark.unit
class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_object_with_start_as_current_span(self) -> None:
        tracer = get_tracer("test_service")
        assert hasattr(tracer, "start_as_current_span")

    def test_get_tracer_returns_object_that_creates_spans(self) -> None:
        tracer = get_tracer("test_service")
        span = tracer.start_as_current_span("test_span")
        assert hasattr(span, "set_attribute")
        assert hasattr(span, "add_event")


@pytest.mark.unit
class TestTraceOperation:
    """Tests for trace_operation context manager."""

    def test_trace_operation_yields_span_like_object(self) -> None:
        tracer = _NoOpTracerStub()
        with trace_operation(tracer, "test_operation") as span:
            assert hasattr(span, "set_attribute")
            assert hasattr(span, "add_event")

    def test_trace_operation_with_attributes_sets_attributes(self) -> None:
        tracer = _NoOpTracerStub()
        with trace_operation(
            tracer,
            "test_operation",
            {"key": "value", "number": "42"},
        ) as span:
            span.add_event("test_event")

    def test_trace_operation_when_exception_raised_propagates(self) -> None:
        tracer = _NoOpTracerStub()
        with pytest.raises(ValueError, match="test error"):
            with trace_operation(tracer, "failing_operation"):
                raise ValueError("test error")

    def test_trace_operation_when_complete_returns_normally(self) -> None:
        tracer = _NoOpTracerStub()
        result = None
        with trace_operation(tracer, "success_operation") as span:
            span.set_attribute("status", "ok")
            result = "completed"
        assert result == "completed"
