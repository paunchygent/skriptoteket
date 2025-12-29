"""Add sandbox_snapshots table and tool_runs.snapshot_id.

Revision ID: 0020
Revises: 0019
Create Date: 2025-12-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0020_sandbox_snapshots"
down_revision: str | None = "0019_draft_locks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "sandbox_snapshots" not in tables:
        op.create_table(
            "sandbox_snapshots",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "tool_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tools.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "draft_head_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("tool_versions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_by_user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("entrypoint", sa.String(128), nullable=False),
            sa.Column("source_code", sa.Text(), nullable=False),
            sa.Column("settings_schema", postgresql.JSONB(), nullable=True),
            sa.Column("input_schema", postgresql.JSONB(), nullable=True),
            sa.Column("usage_instructions", sa.Text(), nullable=True),
            sa.Column("payload_bytes", sa.BigInteger(), nullable=False),
            sa.Column(
                "created_at",
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

        op.create_index("ix_sandbox_snapshots_tool_id", "sandbox_snapshots", ["tool_id"])
        op.create_index(
            "ix_sandbox_snapshots_draft_head_id",
            "sandbox_snapshots",
            ["draft_head_id"],
        )
        op.create_index(
            "ix_sandbox_snapshots_created_by_user_id",
            "sandbox_snapshots",
            ["created_by_user_id"],
        )
        op.create_index(
            "ix_sandbox_snapshots_expires_at",
            "sandbox_snapshots",
            ["expires_at"],
        )
    else:
        indexes = {index["name"] for index in inspector.get_indexes("sandbox_snapshots")}
        if "ix_sandbox_snapshots_tool_id" not in indexes:
            op.create_index("ix_sandbox_snapshots_tool_id", "sandbox_snapshots", ["tool_id"])
        if "ix_sandbox_snapshots_draft_head_id" not in indexes:
            op.create_index(
                "ix_sandbox_snapshots_draft_head_id",
                "sandbox_snapshots",
                ["draft_head_id"],
            )
        if "ix_sandbox_snapshots_created_by_user_id" not in indexes:
            op.create_index(
                "ix_sandbox_snapshots_created_by_user_id",
                "sandbox_snapshots",
                ["created_by_user_id"],
            )
        if "ix_sandbox_snapshots_expires_at" not in indexes:
            op.create_index(
                "ix_sandbox_snapshots_expires_at",
                "sandbox_snapshots",
                ["expires_at"],
            )

    columns = {column["name"] for column in inspector.get_columns("tool_runs")}
    if "snapshot_id" not in columns:
        op.add_column(
            "tool_runs",
            sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("tool_runs")}
    if "tool_runs_snapshot_id_fkey" not in foreign_keys:
        op.create_foreign_key(
            "tool_runs_snapshot_id_fkey",
            "tool_runs",
            "sandbox_snapshots",
            ["snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )

    tool_run_indexes = {index["name"] for index in inspector.get_indexes("tool_runs")}
    if "ix_tool_runs_snapshot_id" not in tool_run_indexes:
        op.create_index("ix_tool_runs_snapshot_id", "tool_runs", ["snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_runs_snapshot_id", table_name="tool_runs")
    op.drop_constraint("tool_runs_snapshot_id_fkey", "tool_runs", type_="foreignkey")
    op.drop_column("tool_runs", "snapshot_id")

    op.drop_index("ix_sandbox_snapshots_expires_at", table_name="sandbox_snapshots")
    op.drop_index("ix_sandbox_snapshots_created_by_user_id", table_name="sandbox_snapshots")
    op.drop_index("ix_sandbox_snapshots_draft_head_id", table_name="sandbox_snapshots")
    op.drop_index("ix_sandbox_snapshots_tool_id", table_name="sandbox_snapshots")
    op.drop_table("sandbox_snapshots")
