"""Allow null layout fields for seating XLSX exports.

Revision ID: 4a9d7c1e2b34
Revises: e4b7c2d9a1f0
Create Date: 2026-03-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "4a9d7c1e2b34"
down_revision: str | Sequence[str] | None = "e4b7c2d9a1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE_NAME = "classroom_planner_seating_export_jobs"


def _table_has_column(*, inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    """Allow non-PDF seating exports to omit PDF-only fields."""

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if _TABLE_NAME not in tables:
        return
    if not _table_has_column(inspector=inspector, table_name=_TABLE_NAME, column_name="layout_id"):
        return
    if not _table_has_column(inspector=inspector, table_name=_TABLE_NAME, column_name="paper_size"):
        return

    op.alter_column(_TABLE_NAME, "layout_id", existing_type=sa.String(length=64), nullable=True)
    op.alter_column(_TABLE_NAME, "paper_size", existing_type=sa.String(length=32), nullable=True)


def downgrade() -> None:
    """Restore the old PDF-only non-null constraint."""

    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if _TABLE_NAME not in tables:
        return
    if not _table_has_column(inspector=inspector, table_name=_TABLE_NAME, column_name="layout_id"):
        return
    if not _table_has_column(inspector=inspector, table_name=_TABLE_NAME, column_name="paper_size"):
        return

    op.execute(
        sa.text(
            """
            UPDATE classroom_planner_seating_export_jobs
            SET
                layout_id = COALESCE(layout_id, 'pretty_brutalist_poster'),
                paper_size = COALESCE(paper_size, 'a3_landscape')
            WHERE export_kind = 'xlsx'
               OR layout_id IS NULL
               OR paper_size IS NULL
            """
        )
    )
    op.alter_column(_TABLE_NAME, "layout_id", existing_type=sa.String(length=64), nullable=False)
    op.alter_column(_TABLE_NAME, "paper_size", existing_type=sa.String(length=32), nullable=False)
