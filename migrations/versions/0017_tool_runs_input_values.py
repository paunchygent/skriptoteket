"""Add input_values column to tool_runs and allow file-less runs.

Revision ID: 0017
Revises: 0016
Create Date: 2025-12-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0017_tool_runs_input_values"
down_revision: str | None = "0016_tool_versions_input_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c["name"]: c for c in inspector.get_columns("tool_runs")}

    if "input_values" not in columns:
        op.add_column(
            "tool_runs",
            sa.Column(
                "input_values",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )

    input_filename = columns.get("input_filename")
    if input_filename is not None and input_filename.get("nullable") is False:
        op.alter_column(
            "tool_runs",
            "input_filename",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    # Prepare for NOT NULL rollback.
    op.execute("UPDATE tool_runs SET input_filename = 'input.bin' WHERE input_filename IS NULL")
    op.alter_column(
        "tool_runs",
        "input_filename",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_column("tool_runs", "input_values")
