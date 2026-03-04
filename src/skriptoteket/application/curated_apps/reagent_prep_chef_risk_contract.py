"""Reagent Prep Chef risk-document contract shared across backend handlers.

This module is the single source of truth for:
1) which local context fields are required before export, and
2) canonical naming for the exported risk-support document.

Related:
  - API models: `skriptoteket.application.curated_apps.reagent_prep_chef`
  - Draft handler: `handlers/reagent_prep_chef_risk_assessment.py`
  - Export/save handlers: `handlers/reagent_prep_chef_export_risk_pdf.py`,
    `handlers/reagent_prep_chef_save_risk_pdf.py`
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.reagent_prep_chef import ReagentPrepChefRiskContext

RISK_SUPPORT_DOCUMENT_TITLE = "Underlag till riskbedömning"
RISK_SUPPORT_PDF_FILENAME = "underlag-riskbedomning.pdf"

REQUIRED_RISK_CONTEXT_FIELDS: tuple[str, ...] = (
    "scope",
    "participants",
    "approver",
    "assessment_date",
    "next_review_date",
)


def _has_text(value: str | None) -> bool:
    return bool((value or "").strip())


def missing_risk_context_fields(*, context: ReagentPrepChefRiskContext | None) -> list[str]:
    """Return required context field keys that are missing for export.

    Args:
        context: Teacher-provided local context in the risk draft.

    Returns:
        Ordered field keys that are missing according to
        `REQUIRED_RISK_CONTEXT_FIELDS`.
    """
    if context is None:
        return list(REQUIRED_RISK_CONTEXT_FIELDS)

    missing: list[str] = []
    if not _has_text(context.scope):
        missing.append("scope")
    if not _has_text(context.participants):
        missing.append("participants")
    if not _has_text(context.approver):
        missing.append("approver")
    if context.assessment_date is None:
        missing.append("assessment_date")
    if context.next_review_date is None:
        missing.append("next_review_date")
    return missing
