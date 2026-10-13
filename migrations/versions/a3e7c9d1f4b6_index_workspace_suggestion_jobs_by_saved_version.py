"""Index workspace suggestion jobs by the saved version they were requested on.

A workspace answer-key suggestion job now records the saved document
revision its request stood on (TASK-SKRIPT-39-04-09), and one saved version
may carry several jobs: one per request. The partial unique index on
``(workspace_lineage_id, workspace_document_revision)`` for workspace jobs is
replaced by a non-unique partial index that also orders by ``created_at``,
so the resume lookup reads the newest job for a saved version in one indexed
query. Only the index changes; no row is touched.

Revision ID: a3e7c9d1f4b6
Revises: f5c2a8d3e7b4
Create Date: 2026-10-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3e7c9d1f4b6"
down_revision: str | Sequence[str] | None = "f5c2a8d3e7b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "exam_answer_key_enrichment_jobs"
_WORKSPACE_ONLY = sa.text("source_kind = 'workspace'")


def upgrade() -> None:
    """Replace the unique workspace revision index with a lookup index."""

    op.drop_index("uq_exam_answer_key_enrichment_jobs_workspace_revision", table_name=_TABLE)
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_workspace_revision",
        _TABLE,
        ["workspace_lineage_id", "workspace_document_revision", "created_at"],
        postgresql_where=_WORKSPACE_ONLY,
    )


def downgrade() -> None:
    """Restore the unique workspace revision index."""

    op.drop_index("ix_exam_answer_key_enrichment_jobs_workspace_revision", table_name=_TABLE)
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        _TABLE,
        ["workspace_lineage_id", "workspace_document_revision"],
        unique=True,
        postgresql_where=_WORKSPACE_ONLY,
    )
