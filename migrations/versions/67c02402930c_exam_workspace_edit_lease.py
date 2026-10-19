"""One editing tab per exam: the edit lease next to the history head (TASK-SKRIPT-40-04-14 K6).

The history head row gains the lease state: the holder tab id, its last renewal
time, and a pending takeover request. A lease not renewed for 15 s is dead; the
holder renews every 5 s. Every step store and position move carries the tab id
and is refused without a live lease.

Revision ID: 67c02402930c
Revises: e8f2c4a6b1d3
Create Date: 2026-10-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

revision: str = "67c02402930c"
down_revision: str | Sequence[str] | None = "e8f2c4a6b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HISTORY_TABLE = "exam_workspace_history"

_LEASE_COLUMNS = (
    ("lease_holder_tab_id", postgresql.UUID(as_uuid=True)),
    ("lease_renewed_at", sa.DateTime(timezone=True)),
    ("lease_takeover_requested_by", postgresql.UUID(as_uuid=True)),
)


def _column_names(*, inspector: Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Store the edit lease next to the history head; no data moves."""

    connection = op.get_bind()
    inspector = inspect(connection)

    columns = _column_names(inspector=inspector, table_name=_HISTORY_TABLE)
    for name, column_type in _LEASE_COLUMNS:
        if name not in columns:
            op.add_column(
                _HISTORY_TABLE,
                sa.Column(name, column_type, nullable=True),
            )


def downgrade() -> None:
    """Drop the edit lease columns; the head row keeps its cursor and position."""

    connection = op.get_bind()
    inspector = inspect(connection)

    columns = _column_names(inspector=inspector, table_name=_HISTORY_TABLE)
    for name, _ in _LEASE_COLUMNS:
        if name in columns:
            op.drop_column(_HISTORY_TABLE, name)
