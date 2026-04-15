"""Auth outcome observability protocol.

Purpose:
    Define the protocol-first seam for Skriptoteket-owned auth outcome
    recording after browser-session authority moved to HuleEdu.

Relationships:
    - Implemented by `skriptoteket.observability.auth_outcomes`.
    - Used by web auth dependencies and the app projection resolver without
      coupling application code to Prometheus or Structlog.
"""

from __future__ import annotations

from typing import Literal, Protocol
from uuid import UUID

AuthContextVerificationOutcome = Literal["accepted", "rejected"]
AuthProjectionOutcome = Literal[
    "resolved",
    "provisioned",
    "missing",
    "blocked_provisioning",
    "linking_required",
    "unsupported_realm",
]
AuthRbacDecision = Literal["denied"]


class AuthOutcomeRecorderProtocol(Protocol):
    """Record bounded auth outcome metrics and structured logs."""

    def record_context_verification(
        self,
        *,
        outcome: AuthContextVerificationOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None: ...

    def record_projection_outcome(
        self,
        *,
        realm: str | None,
        outcome: AuthProjectionOutcome,
        reason: str,
        correlation_id: UUID | None,
    ) -> None: ...

    def record_rbac_decision(
        self,
        *,
        decision: AuthRbacDecision,
        required_role: str,
        actual_role: str,
        route_family: str,
        correlation_id: UUID | None,
    ) -> None: ...
