"""Add input_schema column to tool_versions.

Revision ID: 0016
Revises: 0015
Create Date: 2025-12-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0016_tool_versions_input_schema"
down_revision: str | None = "0015_usage_instructions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c["name"] for c in inspector.get_columns("tool_versions")}

    if "input_schema" not in columns:
        op.add_column(
            "tool_versions",
            sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("tool_versions", "input_schema")
