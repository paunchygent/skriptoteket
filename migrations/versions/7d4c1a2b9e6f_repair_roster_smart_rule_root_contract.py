"""Repair classroom planner roster smart-rule root contract.

This revision heals databases that were stamped to the roster-owned smart-rule
head while still carrying an older partial schema shape. It recreates the
revision-bearing root table when missing, backfills root rows for already
persisted child records, and normalizes child foreign keys back to the root
aggregate so roster-global smart-rule reads stop failing with internal errors.

Revision ID: 7d4c1a2b9e6f
Revises: 6a1e9d3c4b7f
Create Date: 2026-03-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "7d4c1a2b9e6f"
down_revision: str | Sequence[str] | None = "6a1e9d3c4b7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROOT_TABLE = "classroom_planner_roster_smart_rule_sets"
_SEATING_TABLE = "classroom_planner_roster_seating_preferences"
_SEATING_INDEX = "ix_classroom_planner_roster_seating_preferences_roster_id"
_RELATIONSHIP_TABLE = "classroom_planner_roster_relationship_rules"
_RELATIONSHIP_INDEX = "ix_classroom_planner_roster_relationship_rules_roster_id"
_ROSTER_TABLE = "classroom_planner_rosters"


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _foreign_keys(table_name: str) -> list[dict[str, object]]:
    return inspect(op.get_bind()).get_foreign_keys(table_name)


def _create_root_table() -> None:
    op.create_table(
        _ROOT_TABLE,
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["roster_id"],
            [f"{_ROSTER_TABLE}.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("roster_id"),
    )


def _create_seating_table() -> None:
    op.create_table(
        _SEATING_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column(
            "near_teacher",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.ForeignKeyConstraint(
            ["roster_id"],
            [f"{_ROOT_TABLE}.roster_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "roster_id",
            "student_id",
            name="uq_cp_roster_seating_pref",
        ),
    )
    op.create_index(_SEATING_INDEX, _SEATING_TABLE, ["roster_id"], unique=False)


def _create_relationship_table() -> None:
    op.create_table(
        _RELATIONSHIP_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("student_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["roster_id"],
            [f"{_ROOT_TABLE}.roster_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "roster_id",
            "rule_id",
            name="uq_cp_roster_relationship_rule",
        ),
    )
    op.create_index(_RELATIONSHIP_INDEX, _RELATIONSHIP_TABLE, ["roster_id"], unique=False)


def _ensure_root_rows_exist() -> None:
    tables = _table_names()
    source_selects: list[str] = []
    if _SEATING_TABLE in tables:
        source_selects.append(f"SELECT DISTINCT roster_id FROM {_SEATING_TABLE}")
    if _RELATIONSHIP_TABLE in tables:
        source_selects.append(f"SELECT DISTINCT roster_id FROM {_RELATIONSHIP_TABLE}")
    if not source_selects:
        return
    source_sql = "\nUNION\n".join(source_selects)
    op.execute(
        sa.text(
            f"""
            INSERT INTO {_ROOT_TABLE} (roster_id, revision, updated_at)
            SELECT roster_id, 0, NOW()
            FROM ({source_sql}) AS smart_rule_rosters
            ON CONFLICT (roster_id) DO NOTHING
            """
        )
    )


def _ensure_child_foreign_key_points_to_root(table_name: str) -> None:
    table_fks = [
        fk for fk in _foreign_keys(table_name) if fk.get("constrained_columns") == ["roster_id"]
    ]
    for foreign_key in table_fks:
        if foreign_key.get("referred_table") == _ROOT_TABLE:
            return
    for foreign_key in table_fks:
        constraint_name = foreign_key.get("name")
        if constraint_name:
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")
    op.create_foreign_key(
        f"{table_name}_roster_id_fkey",
        table_name,
        _ROOT_TABLE,
        ["roster_id"],
        ["roster_id"],
        ondelete="CASCADE",
    )


def upgrade() -> None:
    """Repair impossible smart-rule schema drift states at the Alembic head."""

    tables = _table_names()
    if _ROOT_TABLE not in tables:
        _create_root_table()
        tables = _table_names()
    if _SEATING_TABLE not in tables:
        _create_seating_table()
        tables = _table_names()
    if _RELATIONSHIP_TABLE not in tables:
        _create_relationship_table()

    _ensure_root_rows_exist()
    _ensure_child_foreign_key_points_to_root(_SEATING_TABLE)
    _ensure_child_foreign_key_points_to_root(_RELATIONSHIP_TABLE)


def downgrade() -> None:
    """Keep the repaired head schema when stepping back to the merge parent."""
