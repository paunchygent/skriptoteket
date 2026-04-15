"""Auth outcome recorder tests.

Purpose:
    Verify the HuleEdu cutover auth outcome recorder emits bounded metrics and
    sanitized structured log fields.

Relationships:
    - Exercises `skriptoteket.observability.auth_outcomes`.
    - Covers the Prometheus metric singleton in
      `skriptoteket.observability.metrics`.
"""

from __future__ import annotations

from uuid import UUID

from prometheus_client import CollectorRegistry, Counter

from skriptoteket.observability import metrics as metrics_module
from skriptoteket.observability.auth_outcomes import PrometheusAuthOutcomeRecorder
from skriptoteket.observability.metrics import AuthOutcomeMetrics, get_auth_outcome_metrics


class RecordingLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, object]]] = []

    def info(self, event: str, **fields: object) -> None:
        self.events.append(("info", event, fields))

    def warning(self, event: str, **fields: object) -> None:
        self.events.append(("warning", event, fields))


def _auth_metrics(registry: CollectorRegistry) -> AuthOutcomeMetrics:
    return {
        "context_verifications_total": Counter(
            "skriptoteket_auth_context_verifications_total",
            "HuleEdu signed internal identity context verification outcomes",
            ["outcome", "reason"],
            registry=registry,
        ),
        "projection_outcomes_total": Counter(
            "skriptoteket_auth_projection_outcomes_total",
            "Realm-aware app projection and provisioning outcomes",
            ["realm", "outcome", "reason"],
            registry=registry,
        ),
        "rbac_decisions_total": Counter(
            "skriptoteket_auth_rbac_decisions_total",
            "Skriptoteket-local RBAC decisions after HuleEdu auth cutover",
            ["decision", "required_role", "actual_role", "route_family"],
            registry=registry,
        ),
    }


def test_context_verification_uses_bounded_metrics_and_structured_event() -> None:
    registry = CollectorRegistry()
    logger = RecordingLogger()
    recorder = PrometheusAuthOutcomeRecorder(metrics=_auth_metrics(registry), logger=logger)
    correlation_id = UUID("565c453d-a6b3-4505-919d-dbbdcb854d7c")

    recorder.record_context_verification(
        outcome="rejected",
        reason="invalid_internal_identity_signature",
        correlation_id=correlation_id,
    )

    assert (
        registry.get_sample_value(
            "skriptoteket_auth_context_verifications_total",
            labels={"outcome": "rejected", "reason": "invalid_internal_identity_signature"},
        )
        == 1
    )
    assert logger.events == [
        (
            "warning",
            "auth.internal_identity.rejected",
            {
                "outcome": "rejected",
                "reason": "invalid_internal_identity_signature",
                "correlation_id": str(correlation_id),
            },
        )
    ]


def test_projection_recorder_sanitizes_unknown_reason_values() -> None:
    registry = CollectorRegistry()
    logger = RecordingLogger()
    recorder = PrometheusAuthOutcomeRecorder(metrics=_auth_metrics(registry), logger=logger)

    recorder.record_projection_outcome(
        realm="skriptoteket_standalone",
        outcome="blocked_provisioning",
        reason="teacher@example.test",
        correlation_id=None,
    )

    assert (
        registry.get_sample_value(
            "skriptoteket_auth_projection_outcomes_total",
            labels={
                "realm": "skriptoteket_standalone",
                "outcome": "blocked_provisioning",
                "reason": "other",
            },
        )
        == 1
    )
    assert logger.events[-1][2]["reason"] == "other"
    assert "teacher@example.test" not in str(logger.events)


def test_rbac_recorder_uses_only_bounded_role_and_route_labels() -> None:
    registry = CollectorRegistry()
    logger = RecordingLogger()
    recorder = PrometheusAuthOutcomeRecorder(metrics=_auth_metrics(registry), logger=logger)

    recorder.record_rbac_decision(
        decision="denied",
        required_role="admin_or_superuser",
        actual_role="contributor",
        route_family="/api/v1/admin/users/123",
        correlation_id=None,
    )

    assert (
        registry.get_sample_value(
            "skriptoteket_auth_rbac_decisions_total",
            labels={
                "decision": "denied",
                "required_role": "admin_or_superuser",
                "actual_role": "contributor",
                "route_family": "other",
            },
        )
        == 1
    )
    assert logger.events[-1][1] == "auth.rbac.denied"
    assert logger.events[-1][2]["route_family"] == "other"


def test_auth_outcome_metric_singleton_recovers_registered_collectors(
    monkeypatch,
) -> None:
    registry = CollectorRegistry()
    monkeypatch.setattr(metrics_module, "REGISTRY", registry)
    monkeypatch.setattr(metrics_module, "_auth_outcome_metrics", None)

    first = get_auth_outcome_metrics()
    monkeypatch.setattr(metrics_module, "_auth_outcome_metrics", None)
    second = get_auth_outcome_metrics()

    assert second["context_verifications_total"] is first["context_verifications_total"]
    assert "skriptoteket_active_sessions" not in registry._names_to_collectors
