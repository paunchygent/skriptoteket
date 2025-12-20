"""OpenTelemetry HTTP tracing middleware.

Extracts W3C Trace Context from incoming requests, creates request spans,
and adds trace/span IDs to response headers for debugging.

Uses route patterns (e.g., /tools/{id}) for span names to maintain consistency
with the metrics middleware.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response

from skriptoteket.observability.tracing import get_tracer

# Paths excluded from tracing (same as metrics)
EXCLUDED_PATHS = frozenset({"/healthz", "/metrics", "/static"})


def _get_route_pattern(request: Request) -> str:
    """Extract the route pattern from the request.

    Returns the route template (e.g., /tools/{id}) instead of the actual path
    for consistent span naming.
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    # Fallback: normalize path for static files
    path = request.url.path
    if path.startswith("/static"):
        return "/static/{file}"
    return path


async def tracing_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Extract trace context and create request span."""
    path = request.url.path

    # Skip tracing for excluded paths
    if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
        return await call_next(request)

    tracer = get_tracer("skriptoteket")

    try:
        from opentelemetry.propagate import extract
        from opentelemetry.trace import Status, StatusCode

        # Extract parent context from W3C Trace Context headers (traceparent)
        ctx = extract(dict(request.headers))

        route_pattern = _get_route_pattern(request)
        span_name = f"{request.method} {route_pattern}"

        with tracer.start_as_current_span(span_name, context=ctx) as span:
            # Set HTTP semantic convention attributes
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.target", path)
            span.set_attribute("http.route", route_pattern)

            # Add correlation ID if available (from CorrelationMiddleware)
            if hasattr(request.state, "correlation_id"):
                span.set_attribute("correlation_id", str(request.state.correlation_id))

            response = await call_next(request)

            # Set response attributes
            span.set_attribute("http.status_code", response.status_code)

            if response.status_code >= 400:
                span.set_status(Status(StatusCode.ERROR))
            else:
                span.set_status(Status(StatusCode.OK))

            # Add trace/span IDs to response headers for debugging
            span_ctx = span.get_span_context()
            if span_ctx.is_valid:
                response.headers["X-Trace-ID"] = format(span_ctx.trace_id, "032x")
                response.headers["X-Span-ID"] = format(span_ctx.span_id, "016x")

            return response

    except ImportError:
        # OpenTelemetry not installed - pass through
        return await call_next(request)
