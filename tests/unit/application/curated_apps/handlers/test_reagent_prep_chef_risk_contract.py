"""Unit tests for the shared Reagent Prep Chef risk contract helpers."""

from __future__ import annotations

from datetime import date

from skriptoteket.application.curated_apps.reagent_prep_chef import ReagentPrepChefRiskContext
from skriptoteket.application.curated_apps.reagent_prep_chef_risk_contract import (
    REQUIRED_RISK_CONTEXT_FIELDS,
    missing_risk_context_fields,
)


def test_missing_risk_context_fields_returns_all_required_when_context_missing() -> None:
    assert missing_risk_context_fields(context=None) == list(REQUIRED_RISK_CONTEXT_FIELDS)


def test_missing_risk_context_fields_trims_strings_and_respects_order() -> None:
    context = ReagentPrepChefRiskContext(
        scope="  ",
        participants="  9A  ",
        approver="",
        assessment_date=None,
        next_review_date=None,
    )

    assert missing_risk_context_fields(context=context) == [
        "scope",
        "approver",
        "assessment_date",
        "next_review_date",
    ]


def test_missing_risk_context_fields_returns_empty_for_complete_required_context() -> None:
    context = ReagentPrepChefRiskContext(
        scope="Sal A: laboration med NaCl-lösning",
        participants="Lärare + klass 9A",
        approver="Ansvarig lärare",
        assessment_date=date(2026, 3, 4),
        next_review_date=date(2026, 9, 1),
    )

    assert missing_risk_context_fields(context=context) == []
