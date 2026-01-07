"""Add tool_session_messages table for editor chat history.

Revision ID: 0024_tool_session_messages
Revises: 0023_input_schema_not_null
Create Date: 2026-01-07
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0024_tool_session_messages"
down_revision: str | None = "0023_input_schema_not_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_session_messages" not in tables:
        op.create_table(
            "tool_session_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tool_session_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tool_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("meta", postgresql.JSONB(), nullable=True),
            sa.Column("sequence", sa.BigInteger(), sa.Identity(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint(
                "tool_session_id",
                "message_id",
                name="uq_tool_session_messages_session_message_id",
            ),
        )
        op.create_index(
            "ix_tool_session_messages_session_sequence",
            "tool_session_messages",
            ["tool_session_id", "sequence"],
        )
        op.create_index(
            "ix_tool_session_messages_session_message_id",
            "tool_session_messages",
            ["tool_session_id", "message_id"],
        )
    else:
        indexes = {index["name"] for index in inspector.get_indexes("tool_session_messages")}
        if "ix_tool_session_messages_session_sequence" not in indexes:
            op.create_index(
                "ix_tool_session_messages_session_sequence",
                "tool_session_messages",
                ["tool_session_id", "sequence"],
            )
        if "ix_tool_session_messages_session_message_id" not in indexes:
            op.create_index(
                "ix_tool_session_messages_session_message_id",
                "tool_session_messages",
                ["tool_session_id", "message_id"],
            )


def downgrade() -> None:
    op.drop_index("ix_tool_session_messages_session_message_id", table_name="tool_session_messages")
    op.drop_index("ix_tool_session_messages_session_sequence", table_name="tool_session_messages")
    op.drop_table("tool_session_messages")
