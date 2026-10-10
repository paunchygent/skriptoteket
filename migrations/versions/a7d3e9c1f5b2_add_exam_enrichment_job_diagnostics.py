"""Persist structured DOCX conversion diagnostics on the job row.

Revision ID: a7d3e9c1f5b2
Revises: e6a9c2f4b8d1
Create Date: 2026-10-10 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7d3e9c1f5b2"
down_revision: str | Sequence[str] | None = "e6a9c2f4b8d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill jobs with an empty diagnostics array."""
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column(
            "diagnostics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Remove the persisted diagnostics column."""
    op.drop_column("exam_answer_key_enrichment_jobs", "diagnostics")
