"""Carry the teacher's selected course on workspace DOCX import jobs.

Revision ID: b7e4d2a9c610
Revises: 1eb507ae2278
Create Date: 2026-10-16 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e4d2a9c610"
down_revision: str | Sequence[str] | None = "1eb507ae2278"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist an optional catalog key independently of the eventual document."""
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("workspace_course_key", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    """Remove the selected import course."""
    op.drop_column("exam_answer_key_enrichment_jobs", "workspace_course_key")
