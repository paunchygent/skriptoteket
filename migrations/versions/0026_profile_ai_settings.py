"""Add allow_remote_fallback to user_profiles.

Revision ID: 0026_profile_ai_settings
Revises: 0025_tool_session_turns
Create Date: 2026-01-13
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0026_profile_ai_settings"
down_revision: str | None = "0025_tool_session_turns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if not _table_has_column(
        inspector=inspector,
        table_name="user_profiles",
        column_name="allow_remote_fallback",
    ):
        op.add_column(
            "user_profiles",
            sa.Column("allow_remote_fallback", sa.Boolean(), nullable=True),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if _table_has_column(
        inspector=inspector,
        table_name="user_profiles",
        column_name="allow_remote_fallback",
    ):
        op.drop_column("user_profiles", "allow_remote_fallback")
