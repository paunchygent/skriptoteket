from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_tool_sessions"
down_revision = "0008_tool_runs_ui_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column(
            "state",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("state_rev", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "tool_id",
            "user_id",
            "context",
            name="uq_tool_sessions_tool_user_context",
        ),
    )
    op.create_index("ix_tool_sessions_user_id", "tool_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_sessions_user_id", table_name="tool_sessions")
    op.drop_table("tool_sessions")
