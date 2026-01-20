"""Add inline_completion_provider to user_profiles.

Revision ID: 0029_profile_inline_completion_provider
Revises: 0028_tool_runs_started_at_drop_default
Create Date: 2026-01-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0029_profile_inline_completion_provider"
down_revision: str | None = "0028_tool_runs_started_at_drop_default"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not _table_has_column(
        inspector=inspector,
        table_name="user_profiles",
        column_name="inline_completion_provider",
    ):
        op.add_column(
            "user_profiles",
            sa.Column("inline_completion_provider", sa.String(length=16), nullable=True),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if _table_has_column(
        inspector=inspector,
        table_name="user_profiles",
        column_name="inline_completion_provider",
    ):
        op.drop_column("user_profiles", "inline_completion_provider")
