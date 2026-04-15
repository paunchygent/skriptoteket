"""Auth outcome recorder for the HuleEdu cutover boundary.

Purpose:
    Emit bounded Prometheus counters and sanitized structured logs for the
    Skriptoteket-owned side of shared auth: signed context verification,
    app projection/provisioning, and local RBAC.

Relationships:
    - Implements `AuthOutcomeRecorderProtocol`.
    - Uses metrics from `skriptoteket.observability.metrics`.
    - Deliberately excludes HuleEdu-owned browser session, CSRF, logout, and
      provider lifecycle telemetry.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

import structlog

from skriptoteket.observability.metrics import AuthOutcomeMetrics, get_auth_outcome_metrics
from skriptoteket.protocols.auth_outcomes import (
    AuthContextVerificationOutcome,
    AuthOutcomeRecorderProtocol,
    AuthProjectionOutcome,
    AuthRbacDecision,
)

_CONTEXT_OUTCOMES = frozenset({"accepted", "rejected"})
_PROJECTION_OUTCOMES = frozenset(
    {
        "resolved",
        "provisioned",
        "missing",
        "blocked_provisioning",
        "linking_required",
        "unsupported_realm",
    }
)
_RBAC_DECISIONS = frozenset({"denied"})
_REALMS = frozenset({"skriptoteket_standalone", "huleedu_school", "unknown"})
_ROLES = frozenset({"user", "contributor", "admin", "superuser", "admin_or_superuser", "unknown"})
_ROUTE_FAMILIES = frozenset(
    {
        "admin",
        "catalog",
        "curated_app",
        "editor",
        "interactive_tool",
        "profile",
        "suggestions",
        "api",
    }
)
_REASONS = frozenset(
    {
        "ok",
        "missing_internal_identity_headers",
        "unsupported_internal_identity_version",
        "missing_internal_identity_key_id",
        "invalid_internal_identity_signature_format",
        "internal_identity_trust_not_configured",
        "unknown_internal_identity_key_id",
        "invalid_internal_identity_signature",
        "invalid_internal_identity_payload",
        "invalid_internal_identity_issuer",
        "invalid_internal_identity_audience",
        "invalid_internal_identity_timestamps",
        "internal_identity_ttl_exceeded",
        "internal_identity_issued_in_future",
        "internal_identity_expired",
        "invalid_huleedu_product_context",
        "invalid_active_app",
        "invalid_active_product_identity_realm",
        "invalid_realm_subject_id",
        "missing_huleedu_app_projection",
        "identity_linking_required",
        "inactive_or_missing_local_user",
        "projection_conflict_unresolved",
        "projection_resolved",
        "projection_conflict_recovered",
        "projection_provisioned",
        "insufficient_permissions",
        "unknown",
    }
)


class AuthOutcomeLoggerProtocol(Protocol):
    """Structured logger methods used by the auth outcome recorder."""

    def info(self, event: str, **fields: object) -> None: ...

    def warning(self, event: str, **fields: object) -> None: ...


def _safe(value: str | None, *, allowed: frozenset[str], default: str = "other") -> str:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in allowed:
        return normalized
    return default


def _correlation(correlation_id: UUID | None) -> str | None:
    return str(correlation_id) if correlation_id is not None else None


class NoopAuthOutcomeRecorder(AuthOutcomeRecorderProtocol):
    """No-op recorder for focused tests and isolated application services."""

    def record_context_verification(
        self,
        *,
        outcome: AuthContextVerificationOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None:
        del outcome, reason, correlation_id

    def record_projection_outcome(
        self,
        *,
        realm: str | None,
        outcome: AuthProjectionOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None:
        del realm, outcome, reason, correlation_id

    def record_rbac_decision(
        self,
        *,
        decision: AuthRbacDecision,
        required_role: str,
        actual_role: str,
        route_family: str,
        correlation_id: UUID | None,
    ) -> None:
        del decision, required_role, actual_role, route_family, correlation_id


class PrometheusAuthOutcomeRecorder(AuthOutcomeRecorderProtocol):
    """Record sanitized auth outcomes through Prometheus counters and Structlog."""

    def __init__(
        self,
        *,
        metrics: AuthOutcomeMetrics | None = None,
        logger: AuthOutcomeLoggerProtocol | None = None,
    ) -> None:
        self._metrics = metrics or get_auth_outcome_metrics()
        self._logger: AuthOutcomeLoggerProtocol = logger or structlog.get_logger(__name__)

    def record_context_verification(
        self,
        *,
        outcome: AuthContextVerificationOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None:
        safe_outcome = _safe(outcome, allowed=_CONTEXT_OUTCOMES)
        safe_reason = _safe(reason, allowed=_REASONS)
        self._metrics["context_verifications_total"].labels(
            outcome=safe_outcome,
            reason=safe_reason,
        ).inc()
        log = self._logger.info if safe_outcome == "accepted" else self._logger.warning
        log(
            "auth.internal_identity.verified"
            if safe_outcome == "accepted"
            else "auth.internal_identity.rejected",
            outcome=safe_outcome,
            reason=safe_reason,
            correlation_id=_correlation(correlation_id),
        )

    def record_projection_outcome(
        self,
        *,
        realm: str | None,
        outcome: AuthProjectionOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None:
        safe_realm = _safe(realm, allowed=_REALMS, default="unknown")
        safe_outcome = _safe(outcome, allowed=_PROJECTION_OUTCOMES)
        safe_reason = _safe(reason, allowed=_REASONS)
        self._metrics["projection_outcomes_total"].labels(
            realm=safe_realm,
            outcome=safe_outcome,
            reason=safe_reason,
        ).inc()
        is_success = safe_outcome in {"resolved", "provisioned"}
        log = self._logger.info if is_success else self._logger.warning
        log(
            "auth.projection.resolved" if is_success else "auth.projection.rejected",
            realm=safe_realm,
            outcome=safe_outcome,
            reason=safe_reason,
            correlation_id=_correlation(correlation_id),
        )

    def record_rbac_decision(
        self,
        *,
        decision: AuthRbacDecision,
        required_role: str,
        actual_role: str,
        route_family: str,
        correlation_id: UUID | None,
    ) -> None:
        safe_decision = _safe(decision, allowed=_RBAC_DECISIONS)
        safe_required = _safe(required_role, allowed=_ROLES)
        safe_actual = _safe(actual_role, allowed=_ROLES, default="unknown")
        safe_route_family = _safe(route_family, allowed=_ROUTE_FAMILIES)
        self._metrics["rbac_decisions_total"].labels(
            decision=safe_decision,
            required_role=safe_required,
            actual_role=safe_actual,
            route_family=safe_route_family,
        ).inc()
        self._logger.warning(
            "auth.rbac.denied",
            decision=safe_decision,
            required_role=safe_required,
            actual_role=safe_actual,
            route_family=safe_route_family,
            correlation_id=_correlation(correlation_id),
        )
