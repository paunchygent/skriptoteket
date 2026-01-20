"""Cache AI settings in sessions.

Revision ID: 0030_sessions_cache_ai_settings
Revises: 0029_profile_inline_completion_provider
Create Date: 2026-01-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0030_sessions_cache_ai_settings"
down_revision: str | None = "0029_profile_inline_completion_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "sessions" not in tables:
        return

    if not _table_has_column(
        inspector=inspector, table_name="sessions", column_name="allow_remote_fallback"
    ):
        op.add_column("sessions", sa.Column("allow_remote_fallback", sa.Boolean(), nullable=True))

    if not _table_has_column(
        inspector=inspector, table_name="sessions", column_name="inline_completion_provider"
    ):
        op.add_column(
            "sessions",
            sa.Column("inline_completion_provider", sa.String(length=16), nullable=True),
        )

    if "user_profiles" not in tables:
        return

    if not _table_has_column(
        inspector=inspector, table_name="user_profiles", column_name="user_id"
    ):
        return
    if not _table_has_column(
        inspector=inspector, table_name="user_profiles", column_name="allow_remote_fallback"
    ):
        return
    if not _table_has_column(
        inspector=inspector, table_name="user_profiles", column_name="inline_completion_provider"
    ):
        return

    op.execute(
        sa.text(
            """
            UPDATE sessions
            SET
                allow_remote_fallback = user_profiles.allow_remote_fallback,
                inline_completion_provider = user_profiles.inline_completion_provider
            FROM user_profiles
            WHERE sessions.user_id = user_profiles.user_id
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "sessions" not in tables:
        return

    if _table_has_column(
        inspector=inspector, table_name="sessions", column_name="inline_completion_provider"
    ):
        op.drop_column("sessions", "inline_completion_provider")

    if _table_has_column(
        inspector=inspector, table_name="sessions", column_name="allow_remote_fallback"
    ):
        op.drop_column("sessions", "allow_remote_fallback")
