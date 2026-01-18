"""Add tool_run_jobs table and truthful tool run lifecycle timestamps.

Revision ID: 0027_tool_run_jobs_execution_queue
Revises: 0026_profile_ai_settings
Create Date: 2026-01-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0027_tool_run_jobs_execution_queue"
down_revision: str | None = "0026_profile_ai_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _column_is_nullable(*, inspector, table_name: str, column_name: str) -> bool | None:
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return bool(column["nullable"])
    return None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "tool_run_jobs" not in tables:
        op.create_table(
            "tool_run_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "run_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tool_runs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("queue", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
            sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False),
            sa.Column(
                "available_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("locked_by", sa.String(length=128), nullable=True),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("run_id", name="uq_tool_run_jobs_run_id"),
        )

        op.create_index(
            "ix_tool_run_jobs_run_id",
            "tool_run_jobs",
            ["run_id"],
        )
        op.create_index(
            "ix_tool_run_jobs_status",
            "tool_run_jobs",
            ["status"],
        )
        op.create_index(
            "ix_tool_run_jobs_claim_order",
            "tool_run_jobs",
            ["status", "available_at", "priority"],
        )
        op.create_index(
            "ix_tool_run_jobs_stale_lease",
            "tool_run_jobs",
            ["status", "locked_until"],
        )

    if "tool_runs" in tables:
        if not _table_has_column(
            inspector=inspector, table_name="tool_runs", column_name="requested_at"
        ):
            op.add_column(
                "tool_runs",
                sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
            )
            op.execute("UPDATE tool_runs SET requested_at = started_at WHERE requested_at IS NULL")
            op.alter_column(
                "tool_runs",
                "requested_at",
                nullable=False,
                server_default=sa.func.now(),
            )
            op.create_index(
                "ix_tool_runs_requested_at",
                "tool_runs",
                ["requested_at"],
            )

        started_at_nullable = _column_is_nullable(
            inspector=inspector, table_name="tool_runs", column_name="started_at"
        )
        if started_at_nullable is False:
            op.alter_column("tool_runs", "started_at", nullable=True)


def downgrade() -> None:
    op.drop_index("ix_tool_runs_requested_at", table_name="tool_runs")
    op.drop_column("tool_runs", "requested_at")

    op.drop_index("ix_tool_run_jobs_stale_lease", table_name="tool_run_jobs")
    op.drop_index("ix_tool_run_jobs_claim_order", table_name="tool_run_jobs")
    op.drop_index("ix_tool_run_jobs_status", table_name="tool_run_jobs")
    op.drop_index("ix_tool_run_jobs_run_id", table_name="tool_run_jobs")
    op.drop_table("tool_run_jobs")
