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
    logins_total: Counter


class IdentityMetrics(TypedDict):
    users_by_role: Gauge


class AuthOutcomeMetrics(TypedDict):
    context_verifications_total: Counter
    projection_outcomes_total: Counter
    rbac_decisions_total: Counter


# Singleton instance
_metrics: Metrics | None = None
_identity_metrics: IdentityMetrics | None = None
_auth_outcome_metrics: AuthOutcomeMetrics | None = None


def get_metrics() -> Metrics:
    """Thread-safe singleton for metrics.

    Returns a dict of registered Prometheus metrics. Safe to call multiple times;
    metrics are only created once.
    """
    global _metrics
    if _metrics is None:
        _metrics = _create_metrics()
    return _metrics


def get_identity_metrics() -> IdentityMetrics:
    """Thread-safe singleton for sensitive identity-related metrics."""
    global _identity_metrics
    if _identity_metrics is None:
        _identity_metrics = _create_identity_metrics()
    return _identity_metrics


def get_auth_outcome_metrics() -> AuthOutcomeMetrics:
    """Thread-safe singleton for HuleEdu cutover auth outcome metrics."""
    global _auth_outcome_metrics
    if _auth_outcome_metrics is None:
        _auth_outcome_metrics = _create_auth_outcome_metrics()
    return _auth_outcome_metrics


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
            "logins_total": Counter(
                "skriptoteket_logins_total",
                "Total login attempts",
                ["status"],
                registry=REGISTRY,
            ),
        }
        return metrics
    except ValueError as e:
        # Handle duplicate registration (e.g., during reload)
        if "Duplicated timeseries" in str(e):
            return _get_existing_metrics()
        raise


def _create_identity_metrics() -> IdentityMetrics:
    try:
        metrics: IdentityMetrics = {
            "users_by_role": Gauge(
                "skriptoteket_users_by_role",
                "Active users by role",
                ["role"],
                registry=REGISTRY,
            ),
        }
        return metrics
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            return _get_existing_identity_metrics()
        raise


def _create_auth_outcome_metrics() -> AuthOutcomeMetrics:
    try:
        metrics: AuthOutcomeMetrics = {
            "context_verifications_total": Counter(
                "skriptoteket_auth_context_verifications_total",
                "HuleEdu signed internal identity context verification outcomes",
                ["outcome", "reason"],
                registry=REGISTRY,
            ),
            "projection_outcomes_total": Counter(
                "skriptoteket_auth_projection_outcomes_total",
                "Realm-aware app projection and provisioning outcomes",
                ["realm", "outcome", "reason"],
                registry=REGISTRY,
            ),
            "rbac_decisions_total": Counter(
                "skriptoteket_auth_rbac_decisions_total",
                "Skriptoteket-local RBAC decisions after HuleEdu auth cutover",
                ["decision", "required_role", "actual_role", "route_family"],
                registry=REGISTRY,
            ),
        }
        return metrics
    except ValueError as e:
        if "Duplicated timeseries" in str(e):
            return _get_existing_auth_outcome_metrics()
        raise


def _registered_collector(metric_name: str) -> object | None:
    collector = REGISTRY._names_to_collectors.get(metric_name)
    if collector is None and metric_name.endswith("_total"):
        collector = REGISTRY._names_to_collectors.get(metric_name.removesuffix("_total"))
    return collector


def _find_registered_counter(metric_name: str) -> Counter | None:
    collector = _registered_collector(metric_name)
    if isinstance(collector, Counter):
        return collector
    return None


def _find_registered_gauge(metric_name: str) -> Gauge | None:
    collector = _registered_collector(metric_name)
    if isinstance(collector, Gauge):
        return collector
    return None


def _find_registered_histogram(metric_name: str) -> Histogram | None:
    collector = _registered_collector(metric_name)
    if isinstance(collector, Histogram):
        return collector
    return None


def _get_existing_metrics() -> Metrics:
    """Retrieve already-registered metrics from the registry.

    Called when metrics were already registered (e.g., hot reload scenario).
    """
    requests_total = _find_registered_counter("skriptoteket_http_requests_total")
    request_duration = _find_registered_histogram("skriptoteket_http_request_duration_seconds")
    session_files_bytes_total = _find_registered_gauge("skriptoteket_session_files_bytes_total")
    session_files_count = _find_registered_gauge("skriptoteket_session_files_count")
    logins_total = _find_registered_counter("skriptoteket_logins_total")

    if (
        requests_total is None
        or request_duration is None
        or session_files_bytes_total is None
        or session_files_count is None
        or logins_total is None
    ):
        raise RuntimeError("Prometheus metrics already registered but could not be retrieved.")

    metrics: Metrics = {
        "http_requests_total": requests_total,
        "http_request_duration_seconds": request_duration,
        "session_files_bytes_total": session_files_bytes_total,
        "session_files_count": session_files_count,
        "logins_total": logins_total,
    }
    return metrics


def _get_existing_identity_metrics() -> IdentityMetrics:
    users_by_role = _find_registered_gauge("skriptoteket_users_by_role")

    if users_by_role is None:
        raise RuntimeError("Identity metrics already registered but could not be retrieved.")

    return {
        "users_by_role": users_by_role,
    }


def _get_existing_auth_outcome_metrics() -> AuthOutcomeMetrics:
    context_verifications_total = _find_registered_counter(
        "skriptoteket_auth_context_verifications_total"
    )
    projection_outcomes_total = _find_registered_counter(
        "skriptoteket_auth_projection_outcomes_total"
    )
    rbac_decisions_total = _find_registered_counter("skriptoteket_auth_rbac_decisions_total")

    if (
        context_verifications_total is None
        or projection_outcomes_total is None
        or rbac_decisions_total is None
    ):
        raise RuntimeError("Auth outcome metrics already registered but could not be retrieved.")

    return {
        "context_verifications_total": context_verifications_total,
        "projection_outcomes_total": projection_outcomes_total,
        "rbac_decisions_total": rbac_decisions_total,
    }
