"""Prometheus HTTP metrics middleware.

Records request count and duration using the singleton metrics from
`skriptoteket.observability.metrics`.

Labels use route patterns (e.g., /tools/{id}) not raw paths to avoid cardinality issues.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response

from skriptoteket.observability.metrics import get_metrics

# Paths excluded from metrics to avoid noise
EXCLUDED_PATHS = frozenset({"/healthz", "/metrics", "/static"})


def _get_route_pattern(request: Request) -> str:
    """Extract the route pattern from the request.

    Returns the route template (e.g., /tools/{id}) instead of the actual path
    to avoid high cardinality in metrics labels.
    """
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return str(route.path)
    # Fallback: normalize path for static files
    path = request.url.path
    if path.startswith("/static"):
        return "/static/{file}"
    return path


async def metrics_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Record HTTP request metrics (count + duration)."""
    path = request.url.path

    # Skip metrics for excluded paths
    if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
        response: Response = await call_next(request)
        return response

    start_time = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start_time

    endpoint = _get_route_pattern(request)
    method = request.method

    # Use singleton metrics
    metrics = get_metrics()
    metrics["http_requests_total"].labels(
        method=method,
        endpoint=endpoint,
        status_code=str(response.status_code),
    ).inc()

    metrics["http_request_duration_seconds"].labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)

    return response
