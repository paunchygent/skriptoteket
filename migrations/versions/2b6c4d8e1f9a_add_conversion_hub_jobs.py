"""Add locally owned Conversion Hub jobs.

Revision ID: 2b6c4d8e1f9a
Revises: 1d3e5f7a9b2c
Create Date: 2026-03-27 10:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "2b6c4d8e1f9a"
down_revision: str | Sequence[str] | None = "1d3e5f7a9b2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the local Conversion Hub job ledger table."""

    op.create_table(
        "conversion_hub_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_filename", sa.String(length=255), nullable=False),
        sa.Column("source_format", sa.String(length=16), nullable=False),
        sa.Column("output_format", sa.String(length=16), nullable=False),
        sa.Column("pdf_paper_size", sa.String(length=16), nullable=True),
        sa.Column("pdf_orientation", sa.String(length=16), nullable=True),
        sa.Column("pdf_margins_mm", sa.Integer(), nullable=True),
        sa.Column("upstream_job_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversion_hub_jobs_owner_user_id",
        "conversion_hub_jobs",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversion_hub_jobs_status",
        "conversion_hub_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_conversion_hub_jobs_owner_created",
        "conversion_hub_jobs",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_conversion_hub_jobs_upstream",
        "conversion_hub_jobs",
        ["upstream_job_id"],
        unique=True,
        postgresql_where=sa.text("upstream_job_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Drop the local Conversion Hub job ledger table."""

    op.drop_index("uq_conversion_hub_jobs_upstream", table_name="conversion_hub_jobs")
    op.drop_index("ix_conversion_hub_jobs_owner_created", table_name="conversion_hub_jobs")
    op.drop_index("ix_conversion_hub_jobs_status", table_name="conversion_hub_jobs")
    op.drop_index("ix_conversion_hub_jobs_owner_user_id", table_name="conversion_hub_jobs")
    op.drop_table("conversion_hub_jobs")
