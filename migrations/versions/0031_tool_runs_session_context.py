"""Add session_context to tool_runs.

Revision ID: 0031_tool_runs_session_context
Revises: 0030_sessions_cache_ai_settings
Create Date: 2026-01-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0031_tool_runs_session_context"
down_revision: str | None = "0030_sessions_cache_ai_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _table_has_index(*, inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_runs" not in tables:
        return

    if not _table_has_column(
        inspector=inspector, table_name="tool_runs", column_name="session_context"
    ):
        op.add_column(
            "tool_runs",
            sa.Column(
                "session_context",
                sa.String(length=64),
                nullable=False,
                server_default="default",
            ),
        )

    if not _table_has_index(
        inspector=inspector,
        table_name="tool_runs",
        index_name="ix_tool_runs_session_context",
    ):
        op.create_index("ix_tool_runs_session_context", "tool_runs", ["session_context"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_runs" not in tables:
        return

    if _table_has_index(
        inspector=inspector,
        table_name="tool_runs",
        index_name="ix_tool_runs_session_context",
    ):
        op.drop_index("ix_tool_runs_session_context", table_name="tool_runs")

    if _table_has_column(
        inspector=inspector, table_name="tool_runs", column_name="session_context"
    ):
        op.drop_column("tool_runs", "session_context")
