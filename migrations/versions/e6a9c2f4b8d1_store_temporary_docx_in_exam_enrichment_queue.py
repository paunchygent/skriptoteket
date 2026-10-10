"""Store temporary DOCX bytes in the existing exam enrichment queue.

Revision ID: e6a9c2f4b8d1
Revises: d4f8b2c6a9e1
Create Date: 2026-10-10 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e6a9c2f4b8d1"
down_revision: str | Sequence[str] | None = "d4f8b2c6a9e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow conversion and enrichment to share a version-one workspace."""
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("source_docx", sa.LargeBinary(), nullable=True),
    )
    op.drop_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        "exam_answer_key_enrichment_jobs",
        ["workspace_lineage_id", "workspace_document_revision"],
        unique=True,
        postgresql_where=sa.text("source_kind = 'workspace'"),
    )
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_docx_import_lineage",
        "exam_answer_key_enrichment_jobs",
        ["workspace_lineage_id"],
        unique=True,
        postgresql_where=sa.text("source_kind = 'docx_import'"),
    )


def downgrade() -> None:
    """Delete imports before restoring the previous shared revision index."""
    op.execute("DELETE FROM exam_answer_key_enrichment_jobs WHERE source_kind = 'docx_import'")
    op.drop_index(
        "uq_exam_answer_key_enrichment_jobs_docx_import_lineage",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        "exam_answer_key_enrichment_jobs",
        ["workspace_lineage_id", "workspace_document_revision"],
        unique=True,
        postgresql_where=sa.text("workspace_lineage_id IS NOT NULL"),
    )
    op.drop_column("exam_answer_key_enrichment_jobs", "source_docx")
