"""Default remaining Smart settings to on.

Purpose:
    Make Smart placement and grouping-specific seating influence opt-out
    settings for newly created authenticated classroom planner drafts.

Relationships:
    - Follows the authenticated history opt-out migration so Smart settings
      exposed in `Avancerade inställningar` default on together.
    - Preserves existing rows because stored false values represent an
      explicit teacher opt-out or older draft state.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8a6d4c2f1b09"
down_revision: str | Sequence[str] | None = "3f6d8a2c4b91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Switch authenticated Smart placement defaults to on."""

    op.alter_column(
        "classroom_planner_plan_drafts",
        "smart_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )

    op.alter_column(
        "classroom_planner_plan_drafts",
        "grouping_seating_distance_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore the previous authenticated Smart placement defaults."""

    op.alter_column(
        "classroom_planner_plan_drafts",
        "grouping_seating_distance_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
    op.alter_column(
        "classroom_planner_plan_drafts",
        "smart_enabled",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
