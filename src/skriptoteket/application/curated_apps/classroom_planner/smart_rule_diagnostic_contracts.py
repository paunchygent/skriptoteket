"""Application DTOs for Klassrumskartan smart-rule diagnostics.

Purpose:
    Serialize solver-owned rule diagnostic categories from the pure domain into
    authenticated and public Smart seating responses without leaking scoring
    internals or frontend-specific marker layout concerns.

Relationships:
    - Consumes `SmartRuleDiagnostic` values from the classroom-planner domain.
    - Shared by the authenticated web router and public guest Smart contracts.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.classroom_planner.seat_support_context import (
    SeatingContext,
)
from skriptoteket.domain.curated_apps.classroom_planner.smart_rule_diagnostics import (
    RuleDiagnosticKind,
    RuleDiagnosticStatus,
    SmartRuleDiagnostic,
)


class SmartRuleDiagnosticDto(BaseModel):
    """Serialize one display-safe solver-owned smart-rule diagnostic."""

    model_config = ConfigDict(frozen=True)

    rule_id: str | None = None
    rule_kind: RuleDiagnosticKind
    status: RuleDiagnosticStatus
    student_ids: list[str] = Field(default_factory=list)
    seat_ids: list[str] = Field(default_factory=list)
    reason_code: str
    relation_mode: str | None = None
    seating_context: SeatingContext | None = None
    message_key: str | None = None


def serialize_smart_rule_diagnostics(
    diagnostics: tuple[SmartRuleDiagnostic, ...],
) -> list[SmartRuleDiagnosticDto]:
    """Convert domain diagnostics into stable API DTOs."""

    return [
        SmartRuleDiagnosticDto(
            rule_id=diagnostic.rule_id,
            rule_kind=diagnostic.rule_kind,
            status=diagnostic.status,
            student_ids=list(diagnostic.student_ids),
            seat_ids=list(diagnostic.seat_ids),
            reason_code=diagnostic.reason_code,
            relation_mode=diagnostic.relation_mode,
            seating_context=diagnostic.seating_context,
            message_key=diagnostic.message_key,
        )
        for diagnostic in diagnostics
    ]
