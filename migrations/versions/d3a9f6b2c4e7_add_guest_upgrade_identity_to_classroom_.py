"""Add guest-upgrade identity fields to classroom planner drafts.

Purpose:
    Persist the authenticated guest-upgrade metadata needed for durable
    imported-draft idempotency and for preserving the task-entry classroom
    selection mode on imported historical drafts.

Relationships:
    - Extends `classroom_planner_plan_drafts` after the current planner head.
    - Supports PR-0221 authenticated guest-upgrade orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3a9f6b2c4e7"
down_revision: str | Sequence[str] | None = "b7f9c2d4e1a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "classroom_planner_plan_drafts"
_INDEX = "uq_cp_guest_import_identity"


def upgrade() -> None:
    """Add durable guest-upgrade draft metadata."""

    op.add_column(
        _TABLE,
        sa.Column(
            "task_entry_classroom_selection_mode",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'optional'"),
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column(
            "guest_import_identity",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.create_index(
        _INDEX,
        _TABLE,
        ["owner_user_id", "guest_import_identity"],
        unique=True,
        postgresql_where=sa.text("guest_import_identity IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove durable guest-upgrade draft metadata."""

    op.drop_index(_INDEX, table_name=_TABLE)
    op.drop_column(_TABLE, "guest_import_identity")
    op.drop_column(_TABLE, "task_entry_classroom_selection_mode")
