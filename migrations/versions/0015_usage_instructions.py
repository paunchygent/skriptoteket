"""Add usage_instructions column to tool_versions.

Revision ID: 0015
Revises: 0014
Create Date: 2025-12-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0015_usage_instructions"
down_revision: str | None = "0014_tool_versions_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make idempotent: check if column exists before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c["name"] for c in inspector.get_columns("tool_versions")}

    if "usage_instructions" not in columns:
        op.add_column(
            "tool_versions",
            sa.Column("usage_instructions", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("tool_versions", "usage_instructions")
