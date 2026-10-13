"""Store editor-sent content and suggestions on workspace enrichment jobs.

Workspace answer-key suggestion jobs (TASK-SKRIPT-39-04-07) run on the
questions exactly as the editor shows them, so the sent answer-key views
and the suggestions the job produced live on the job row itself instead of
any saved document revision or overlay record. The workspace's rows in
``exam_answer_key_proposed_overlays`` are deleted; DigiExam rows (a
conversion job binding, no workspace lineage) stay, because the DigiExam
converter keeps storing its proposals in that table (P10).

Revision ID: f5c2a8d3e7b4
Revises: c4f8a2d6b9e1
Create Date: 2026-10-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f5c2a8d3e7b4"
down_revision: str | Sequence[str] | None = "c4f8a2d6b9e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the sent-content and suggestion payload columns to enrichment jobs."""

    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("workspace_request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column(
            "workspace_suggestions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.execute(
        "DELETE FROM exam_answer_key_proposed_overlays WHERE workspace_lineage_id IS NOT NULL"
    )


def downgrade() -> None:
    """Remove the workspace suggestion payload columns.

    The deleted workspace overlay rows cannot be restored; they were
    pending proposals for saved revisions, superseded by suggestions kept
    on each question.
    """

    op.drop_column("exam_answer_key_enrichment_jobs", "workspace_suggestions_json")
    op.drop_column("exam_answer_key_enrichment_jobs", "workspace_request_json")
