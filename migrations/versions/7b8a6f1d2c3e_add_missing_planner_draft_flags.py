"""Add missing classroom planner draft flag columns.

This revision brings the live `classroom_planner_plan_drafts` table back in
sync with the draft ORM after the planner fundamentals model added the
history and grouping-distance flags. The columns are boolean feature flags
with safe false defaults so existing drafts remain readable immediately.

Revision ID: 7b8a6f1d2c3e
Revises: f6c1e2a9b3d4
Create Date: 2026-03-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "7b8a6f1d2c3e"
down_revision: str | Sequence[str] | None = "f6c1e2a9b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "classroom_planner_plan_drafts"


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    """Add the missing planner draft flags with safe defaults."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if _TABLE_NAME not in tables:
        return

    if not _table_has_column(
        inspector=inspector,
        table_name=_TABLE_NAME,
        column_name="use_history",
    ):
        op.add_column(
            _TABLE_NAME,
            sa.Column(
                "use_history",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if not _table_has_column(
        inspector=inspector,
        table_name=_TABLE_NAME,
        column_name="grouping_seating_distance_enabled",
    ):
        op.add_column(
            _TABLE_NAME,
            sa.Column(
                "grouping_seating_distance_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    """Remove the planner draft flag columns."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if _TABLE_NAME not in tables:
        return

    if _table_has_column(
        inspector=inspector,
        table_name=_TABLE_NAME,
        column_name="grouping_seating_distance_enabled",
    ):
        op.drop_column(_TABLE_NAME, "grouping_seating_distance_enabled")

    if _table_has_column(
        inspector=inspector,
        table_name=_TABLE_NAME,
        column_name="use_history",
    ):
        op.drop_column(_TABLE_NAME, "use_history")
