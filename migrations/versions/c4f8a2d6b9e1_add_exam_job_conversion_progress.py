"""Persist progressive DOCX conversion state on the job row.

Revision ID: c4f8a2d6b9e1
Revises: e3b7a1c5d9f2
Create Date: 2026-10-11 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4f8a2d6b9e1"
down_revision: str | Sequence[str] | None = "e3b7a1c5d9f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable progress column; existing jobs carry no progress."""
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("conversion_progress", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    """Remove the persisted conversion progress column."""
    op.drop_column("exam_answer_key_enrichment_jobs", "conversion_progress")
