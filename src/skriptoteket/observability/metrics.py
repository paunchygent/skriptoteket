"""Prometheus metrics singleton for Skriptoteket.

Follows HuleEdu naming convention: {service}_{subsystem}_{metric}_{unit}

Example metrics:
- skriptoteket_http_requests_total
- skriptoteket_http_request_duration_seconds
"""

from __future__ import annotations

from typing import TypedDict

from prometheus_client import REGISTRY, Counter, Histogram


class Metrics(TypedDict):
    http_requests_total: Counter
    http_request_duration_seconds: Histogram


# Singleton instance
_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    """Thread-safe singleton for metrics.

    Returns a dict of registered Prometheus metrics. Safe to call multiple times;
    metrics are only created once.
    """
    global _metrics
    if _metrics is None:
        _metrics = _create_metrics()
    return _metrics


def _create_metrics() -> Metrics:
    """Create and register Prometheus metrics.

    Uses REGISTRY to check for existing metrics (handles reload scenarios).
    """
    try:
        metrics: Metrics = {
            "http_requests_total": Counter(
                "skriptoteket_http_requests_total",
                "Total HTTP requests",
                ["method", "endpoint", "status_code"],
                registry=REGISTRY,
            ),
            "http_request_duration_seconds": Histogram(
                "skriptoteket_http_request_duration_seconds",
                "HTTP request duration in seconds",
                ["method", "endpoint"],
                buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
                registry=REGISTRY,
            ),
        }
        return metrics
    except ValueError as e:
        # Handle duplicate registration (e.g., during reload)
        if "Duplicated timeseries" in str(e):
            return _get_existing_metrics()
        raise


def _get_existing_metrics() -> Metrics:
    """Retrieve already-registered metrics from the registry.

    Called when metrics were already registered (e.g., hot reload scenario).
    """
    requests_total: Counter | None = None
    request_duration: Histogram | None = None

    # Find existing metrics in the registry
    for collector in REGISTRY._names_to_collectors.values():
        name = getattr(collector, "_name", None)
        if name == "skriptoteket_http_requests_total" and isinstance(collector, Counter):
            requests_total = collector
            continue
        if name == "skriptoteket_http_request_duration_seconds" and isinstance(
            collector, Histogram
        ):
            request_duration = collector

    if requests_total is None or request_duration is None:
        raise RuntimeError("Prometheus metrics already registered but could not be retrieved.")

    metrics: Metrics = {
        "http_requests_total": requests_total,
        "http_request_duration_seconds": request_duration,
    }
    return metrics
