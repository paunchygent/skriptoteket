"""Add classroom planner guest-upgrade consumption ledger.

Purpose:
    Persist the one-time authenticated guest-upgrade consumption fact for
    Klassrumskartan without inferring that policy from planner drafts or
    checkpoints.

Relationships:
    - Adds `classroom_planner_guest_upgrade_consumptions` after the current
      guest-upgrade/idempotency planner head.
    - Supports PR-0246 one-time guest-upgrade consumption truth.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0f4c2d7a9b1e"
down_revision: str | Sequence[str] | None = "d3a9f6b2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "classroom_planner_guest_upgrade_consumptions"
_INDEX = "uq_cp_guest_upgrade_consumptions_owner_app"


def upgrade() -> None:
    """Create the guest-upgrade consumption ledger table."""

    op.create_table(
        _TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("app_id", sa.String(length=255), nullable=False),
        sa.Column("snapshot_id", sa.String(length=255), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(_INDEX, _TABLE, ["owner_user_id", "app_id"], unique=True)
    op.create_index(
        op.f("ix_classroom_planner_guest_upgrade_consumptions_owner_user_id"),
        _TABLE,
        ["owner_user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the guest-upgrade consumption ledger table."""

    op.drop_index(
        op.f("ix_classroom_planner_guest_upgrade_consumptions_owner_user_id"),
        table_name=_TABLE,
    )
    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_table(_TABLE)
