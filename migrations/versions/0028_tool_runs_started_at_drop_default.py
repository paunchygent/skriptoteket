"""Drop tool_runs.started_at server default.

Revision ID: 0028_tool_runs_started_at_drop_default
Revises: 0027_tool_run_jobs_execution_queue
Create Date: 2026-01-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0028_tool_runs_started_at_drop_default"
down_revision: str | None = "0027_tool_run_jobs_execution_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_runs" not in tables:
        return
    if not _table_has_column(inspector=inspector, table_name="tool_runs", column_name="started_at"):
        return

    op.alter_column(
        "tool_runs",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_runs" not in tables:
        return
    if not _table_has_column(inspector=inspector, table_name="tool_runs", column_name="started_at"):
        return

    op.alter_column(
        "tool_runs",
        "started_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
        server_default=sa.func.now(),
    )
