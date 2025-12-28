"""Add draft_locks table.

Revision ID: 0019
Revises: 0018
Create Date: 2025-12-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0019_draft_locks"
down_revision: str | None = "0018_user_favorite_tools_and_apps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "draft_locks" not in tables:
        op.create_table(
            "draft_locks",
            sa.Column("tool_id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("draft_head_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "locked_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "forced_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "locked_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "expires_at",
                sa.DateTime(timezone=True),
                nullable=False,
            ),
        )

        op.create_index(
            "ix_draft_locks_expires_at",
            "draft_locks",
            ["expires_at"],
        )
        op.create_index(
            "ix_draft_locks_draft_head_id",
            "draft_locks",
            ["draft_head_id"],
        )
        op.create_index(
            "ix_draft_locks_locked_by_user_id",
            "draft_locks",
            ["locked_by_user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_draft_locks_locked_by_user_id", table_name="draft_locks")
    op.drop_index("ix_draft_locks_draft_head_id", table_name="draft_locks")
    op.drop_index("ix_draft_locks_expires_at", table_name="draft_locks")
    op.drop_table("draft_locks")
