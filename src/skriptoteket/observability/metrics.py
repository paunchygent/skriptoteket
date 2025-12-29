"""Prometheus metrics singleton for Skriptoteket.

Follows HuleEdu naming convention: {service}_{subsystem}_{metric}_{unit}

Example metrics:
- skriptoteket_http_requests_total
- skriptoteket_http_request_duration_seconds
"""

from __future__ import annotations

from typing import TypedDict

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


class Metrics(TypedDict):
    http_requests_total: Counter
    http_request_duration_seconds: Histogram
    session_files_bytes_total: Gauge
    session_files_count: Gauge
    active_sessions: Gauge
    logins_total: Counter
    users_by_role: Gauge


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
            "session_files_bytes_total": Gauge(
                "skriptoteket_session_files_bytes_total",
                "Total bytes of stored session files (excluding meta.json)",
                registry=REGISTRY,
            ),
            "session_files_count": Gauge(
                "skriptoteket_session_files_count",
                "Count of stored session files (excluding meta.json)",
                registry=REGISTRY,
            ),
            "active_sessions": Gauge(
                "skriptoteket_active_sessions",
                "Current count of active user sessions",
                registry=REGISTRY,
            ),
            "logins_total": Counter(
                "skriptoteket_logins_total",
                "Total login attempts",
                ["status"],
                registry=REGISTRY,
            ),
            "users_by_role": Gauge(
                "skriptoteket_users_by_role",
                "Active users by role",
                ["role"],
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
    session_files_bytes_total: Gauge | None = None
    session_files_count: Gauge | None = None
    active_sessions: Gauge | None = None
    logins_total: Counter | None = None
    users_by_role: Gauge | None = None

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
            continue
        if name == "skriptoteket_session_files_bytes_total" and isinstance(collector, Gauge):
            session_files_bytes_total = collector
            continue
        if name == "skriptoteket_session_files_count" and isinstance(collector, Gauge):
            session_files_count = collector
            continue
        if name == "skriptoteket_active_sessions" and isinstance(collector, Gauge):
            active_sessions = collector
            continue
        if name == "skriptoteket_logins_total" and isinstance(collector, Counter):
            logins_total = collector
            continue
        if name == "skriptoteket_users_by_role" and isinstance(collector, Gauge):
            users_by_role = collector

    if (
        requests_total is None
        or request_duration is None
        or session_files_bytes_total is None
        or session_files_count is None
        or active_sessions is None
        or logins_total is None
        or users_by_role is None
    ):
        raise RuntimeError("Prometheus metrics already registered but could not be retrieved.")

    metrics: Metrics = {
        "http_requests_total": requests_total,
        "http_request_duration_seconds": request_duration,
        "session_files_bytes_total": session_files_bytes_total,
        "session_files_count": session_files_count,
        "active_sessions": active_sessions,
        "logins_total": logins_total,
        "users_by_role": users_by_role,
    }
    return metrics
