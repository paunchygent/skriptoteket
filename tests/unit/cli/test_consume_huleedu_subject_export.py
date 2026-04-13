"""Unit tests for the HuleEdu subject export consumer CLI.

Purpose:
    Keep operator-facing subject export summaries aligned with dry-run and
    apply semantics.

Relationships:
    - Exercises CLI formatting without opening database sessions.
    - Complements application-layer subject export consumer tests.
"""

from __future__ import annotations

from skriptoteket.application.identity.huleedu_subject_export_consumer import (
    HuleEduSubjectExportResult,
)
from skriptoteket.cli.commands.consume_huleedu_subject_export import (
    format_subject_export_result_summary,
)


def test_dry_run_summary_reports_planned_counters() -> None:
    result = HuleEduSubjectExportResult(
        dry_run=True,
        processed=3,
        created_users=0,
        created_projections=0,
        updated_users=0,
        would_create_users=3,
        would_create_projections=3,
        would_update_users=0,
        unchanged=0,
        account_results=[],
    )

    assert format_subject_export_result_summary(result) == (
        "HuleEdu subject export dry-run ok: processed=3, "
        "would_create_users=3, would_create_projections=3, "
        "would_update_users=0, unchanged=0"
    )


def test_apply_summary_reports_applied_counters() -> None:
    result = HuleEduSubjectExportResult(
        dry_run=False,
        processed=3,
        created_users=2,
        created_projections=2,
        updated_users=1,
        would_create_users=0,
        would_create_projections=0,
        would_update_users=0,
        unchanged=0,
        account_results=[],
    )

    assert format_subject_export_result_summary(result) == (
        "HuleEdu subject export apply ok: processed=3, "
        "created_users=2, created_projections=2, updated_users=1, unchanged=0"
    )
