"""Add exam guest draft handoff ledger.

Purpose:
    Persist the one-time sign-in handoff fact for exam workspace guest drafts so
    a repeated or concurrent post of the same (owner, draft) creates exactly one
    exam in Mina filer (TASK-SKRIPT-41-02-02 P5).

Relationships:
    - Adds `exam_guest_draft_handoffs` after the public request windows head.
    - Mirrors the idempotency ledger shape of
      `classroom_planner_guest_upgrade_consumptions`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8e4f2a6d9b3"
down_revision: str | Sequence[str] | None = "a1c2e3f4b5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "exam_guest_draft_handoffs"


def upgrade() -> None:
    """Create the per-owner guest draft handoff ledger table."""

    op.create_table(
        _TABLE,
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("owner_user_id", "draft_id"),
    )


def downgrade() -> None:
    """Drop the guest draft handoff ledger table."""

    op.drop_table(_TABLE)
