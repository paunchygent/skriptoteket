"""Per-step undo history and once-per-exam pictures (TASK-SKRIPT-40-04-14 K9).

One row per exam used to hold the whole undo history as one JSON blob, with
every step carrying a full container zip including every picture. Every change
read and rewrote the whole blob. This revision replaces that format:

- `exam_workspace_history` keeps only the cursor, the current step id and the
  baseline step id; its `content` blob column goes.
- `exam_workspace_history_steps` holds one row per step: the step's document
  without picture bytes (zlib-compressed JSON), its append position, its asset
  references and its notes.
- `exam_workspace_history_assets` holds one row per (exam, picture): the bytes.

The old blob rows are unreadable (no reader for the old format), so they are
dropped. The application recreates the baseline from the saved exam file on
the next open, so every migrated exam keeps opening.

Revision ID: e8f2c4a6b1d3
Revises: c8e4f2a6d9b3
Create Date: 2026-10-19 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

revision: str = "e8f2c4a6b1d3"
down_revision: str | Sequence[str] | None = "c8e4f2a6d9b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HISTORY_TABLE = "exam_workspace_history"
_STEPS_TABLE = "exam_workspace_history_steps"
_ASSETS_TABLE = "exam_workspace_history_assets"
_ORDER_INDEX = "ix_exam_workspace_history_steps_order"


def _table_names(*, inspector: Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(*, inspector: Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(*, inspector: Inspector, table_name: str) -> set[str]:
    names: set[str] = set()
    for index in inspector.get_indexes(table_name):
        if index["name"] is not None:
            names.add(index["name"])
    return names


def upgrade() -> None:
    """Store each undo step and each picture in its own row; drop the history blob."""

    connection = op.get_bind()
    inspector = inspect(connection)

    connection.execute(
        sa.text(f"DELETE FROM {_HISTORY_TABLE}"),
    )

    columns = _column_names(inspector=inspector, table_name=_HISTORY_TABLE)
    if "content" in columns:
        op.drop_column(_HISTORY_TABLE, "content")
    for name in ("cursor", "current_step_id", "baseline_step_id"):
        if name not in columns:
            op.add_column(
                _HISTORY_TABLE,
                sa.Column(
                    name,
                    postgresql.UUID(as_uuid=True),
                    nullable=False,
                ),
            )

    if _STEPS_TABLE not in _table_names(inspector=inspector):
        op.create_table(
            _STEPS_TABLE,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("step_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("document", sa.LargeBinary(), nullable=False),
            sa.Column(
                "asset_ids",
                postgresql.ARRAY(sa.Text()),
                nullable=False,
            ),
            sa.Column(
                "notes",
                postgresql.ARRAY(sa.Text()),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "lineage_id", "step_id"),
        )
    if _ORDER_INDEX not in _index_names(inspector=inspector, table_name=_STEPS_TABLE):
        op.create_index(
            _ORDER_INDEX,
            _STEPS_TABLE,
            ["user_id", "lineage_id", "position"],
        )

    if _ASSETS_TABLE not in _table_names(inspector=inspector):
        op.create_table(
            _ASSETS_TABLE,
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("lineage_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("asset_id", sa.String(length=64), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "lineage_id", "asset_id"),
        )


def downgrade() -> None:
    """Drop the step and picture rows; the history blob column comes back empty."""

    connection = op.get_bind()
    inspector = inspect(connection)

    if _ASSETS_TABLE in _table_names(inspector=inspector):
        op.drop_table(_ASSETS_TABLE)
    if _STEPS_TABLE in _table_names(inspector=inspector):
        op.drop_table(_STEPS_TABLE)

    columns = _column_names(inspector=inspector, table_name=_HISTORY_TABLE)
    for name in ("baseline_step_id", "current_step_id", "cursor"):
        if name in columns:
            op.drop_column(_HISTORY_TABLE, name)
    if "content" not in columns:
        op.add_column(
            _HISTORY_TABLE,
            sa.Column("content", sa.LargeBinary(), nullable=False),
        )
