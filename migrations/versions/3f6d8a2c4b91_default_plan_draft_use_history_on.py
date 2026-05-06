"""Default authenticated classroom planner history to on.

Purpose:
    Make account-backed Smart history an opt-out draft setting for newly
    created authenticated grouping and seating drafts.

Relationships:
    - Keeps existing draft rows unchanged because an existing false value is
      the only persisted representation of an explicit opt-out.
    - Leaves public guest snapshot contracts on their separate browser-owned
      no-history lane.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3f6d8a2c4b91"
down_revision: str | Sequence[str] | None = "0d9c5e8a2f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Switch the authenticated draft server default to history on."""

    op.alter_column(
        "classroom_planner_plan_drafts",
        "use_history",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Restore the previous authenticated draft server default."""

    op.alter_column(
        "classroom_planner_plan_drafts",
        "use_history",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
