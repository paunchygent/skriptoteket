"""Generalize answer-key enrichment jobs for the exam workspace lane.

The existing `exam_answer_key_enrichment_jobs` queue gains a `source_kind`
discriminator (TASK-SKRIPT-39-04-01, "no second queue"): DigiExam rows keep
their conversion binding; workspace rows pin a Mina filer document lineage
and revision instead. Proposed overlays gain the matching nullable workspace
binding so proposal records stay in the existing table.

Revision ID: d4f8b2c6a9e1
Revises: 7c3e9a1d4f20
Create Date: 2026-10-09 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4f8b2c6a9e1"
down_revision: str | Sequence[str] | None = "7c3e9a1d4f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the workspace source lane to enrichment jobs and proposed overlays."""

    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("source_kind", sa.String(length=32), nullable=False, server_default="dxe"),
    )
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("workspace_lineage_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("workspace_document_revision", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "conversion_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "source_dxe",
        existing_type=sa.LargeBinary(),
        nullable=True,
    )
    op.create_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        "exam_answer_key_enrichment_jobs",
        ["workspace_lineage_id", "workspace_document_revision"],
        unique=True,
        postgresql_where=sa.text("workspace_lineage_id IS NOT NULL"),
    )

    op.add_column(
        "exam_answer_key_proposed_overlays",
        sa.Column("workspace_lineage_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "exam_answer_key_proposed_overlays",
        sa.Column("workspace_document_revision", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "exam_answer_key_proposed_overlays",
        "conversion_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    """Remove the workspace source lane; workspace rows cannot survive it."""

    op.execute("DELETE FROM exam_answer_key_proposed_overlays WHERE conversion_job_id IS NULL")
    op.execute("DELETE FROM exam_answer_key_enrichment_jobs WHERE source_kind <> 'dxe'")

    op.alter_column(
        "exam_answer_key_proposed_overlays",
        "conversion_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("exam_answer_key_proposed_overlays", "workspace_document_revision")
    op.drop_column("exam_answer_key_proposed_overlays", "workspace_lineage_id")

    op.drop_index(
        "uq_exam_answer_key_enrichment_jobs_workspace_revision",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "source_dxe",
        existing_type=sa.LargeBinary(),
        nullable=False,
    )
    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "conversion_job_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("exam_answer_key_enrichment_jobs", "workspace_document_revision")
    op.drop_column("exam_answer_key_enrichment_jobs", "workspace_lineage_id")
    op.drop_column("exam_answer_key_enrichment_jobs", "source_kind")
