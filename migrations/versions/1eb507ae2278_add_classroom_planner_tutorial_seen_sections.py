"""Add the classroom planner tutorial seen-sections profile column.

Signed-in teachers' seen Klassrumskartan tutorial sections
(TASK-SKRIPT-08-36-01) persist on the user profile as a nullable JSON list of
section ids, so the first-use tutorial dialog stays closed across browsers.

Revision ID: 1eb507ae2278
Revises: a3e7c9d1f4b6
Create Date: 2026-10-15 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1eb507ae2278"
down_revision: str | Sequence[str] | None = "a3e7c9d1f4b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "user_profiles"
_COLUMN = "classroom_planner_tutorial_seen_sections"


def upgrade() -> None:
    """Add the nullable seen-sections list column."""

    op.add_column(
        _TABLE,
        sa.Column(_COLUMN, postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Drop the seen-sections list column."""

    op.drop_column(_TABLE, _COLUMN)
