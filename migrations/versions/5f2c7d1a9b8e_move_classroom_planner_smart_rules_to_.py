"""Move classroom planner smart rules from drafts to roster ownership.

This revision resets the persistence boundary for Klassrumskartan smart rules.
Relationship rules and near-teacher preferences belong to the class roster, not
to one mutable draft workspace, so the old draft-owned tables are dropped and
replaced by roster-owned equivalents.

Revision ID: 5f2c7d1a9b8e
Revises: 1d3e5f7a9b2c
Create Date: 2026-03-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "5f2c7d1a9b8e"
down_revision: str | Sequence[str] | None = "1d3e5f7a9b2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DRAFT_SEATING_PREF_TABLE = "classroom_planner_student_seating_preferences"
_DRAFT_SEATING_PREF_INDEX = "ix_classroom_planner_student_seating_preferences_draft_id"
_DRAFT_RELATIONSHIP_TABLE = "classroom_planner_relationship_rules"
_DRAFT_RELATIONSHIP_INDEX = "ix_classroom_planner_relationship_rules_draft_id"
_ROSTER_SMART_RULE_SET_TABLE = "classroom_planner_roster_smart_rule_sets"
_ROSTER_SEATING_PREF_TABLE = "classroom_planner_roster_seating_preferences"
_ROSTER_SEATING_PREF_INDEX = "ix_classroom_planner_roster_seating_preferences_roster_id"
_ROSTER_RELATIONSHIP_TABLE = "classroom_planner_roster_relationship_rules"
_ROSTER_RELATIONSHIP_INDEX = "ix_classroom_planner_roster_relationship_rules_roster_id"


def upgrade() -> None:
    """Move smart-rule storage from draft scope to roster scope."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _ROSTER_SMART_RULE_SET_TABLE not in tables:
        op.create_table(
            _ROSTER_SMART_RULE_SET_TABLE,
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
                ["classroom_planner_rosters.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("roster_id"),
        )

    if _ROSTER_SEATING_PREF_TABLE not in tables:
        op.create_table(
            _ROSTER_SEATING_PREF_TABLE,
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
                [f"{_ROSTER_SMART_RULE_SET_TABLE}.roster_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "roster_id",
                "student_id",
                name="uq_cp_roster_seating_pref",
            ),
        )
        op.create_index(
            _ROSTER_SEATING_PREF_INDEX,
            _ROSTER_SEATING_PREF_TABLE,
            ["roster_id"],
            unique=False,
        )

    if _ROSTER_RELATIONSHIP_TABLE not in tables:
        op.create_table(
            _ROSTER_RELATIONSHIP_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rule_id", sa.String(length=255), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("student_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.ForeignKeyConstraint(
                ["roster_id"],
                [f"{_ROSTER_SMART_RULE_SET_TABLE}.roster_id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "roster_id",
                "rule_id",
                name="uq_cp_roster_relationship_rule",
            ),
        )
        op.create_index(
            _ROSTER_RELATIONSHIP_INDEX,
            _ROSTER_RELATIONSHIP_TABLE,
            ["roster_id"],
            unique=False,
        )

    if _DRAFT_SEATING_PREF_TABLE in tables:
        draft_seating_indexes = {
            index["name"] for index in inspector.get_indexes(_DRAFT_SEATING_PREF_TABLE)
        }
        if _DRAFT_SEATING_PREF_INDEX in draft_seating_indexes:
            op.drop_index(_DRAFT_SEATING_PREF_INDEX, table_name=_DRAFT_SEATING_PREF_TABLE)
        op.drop_table(_DRAFT_SEATING_PREF_TABLE)

    if _DRAFT_RELATIONSHIP_TABLE in tables:
        draft_relationship_indexes = {
            index["name"] for index in inspector.get_indexes(_DRAFT_RELATIONSHIP_TABLE)
        }
        if _DRAFT_RELATIONSHIP_INDEX in draft_relationship_indexes:
            op.drop_index(_DRAFT_RELATIONSHIP_INDEX, table_name=_DRAFT_RELATIONSHIP_TABLE)
        op.drop_table(_DRAFT_RELATIONSHIP_TABLE)


def downgrade() -> None:
    """Restore draft-owned smart-rule tables and remove roster-owned ones."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _DRAFT_SEATING_PREF_TABLE not in tables:
        op.create_table(
            _DRAFT_SEATING_PREF_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("student_id", sa.String(length=255), nullable=False),
            sa.Column(
                "near_teacher",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.ForeignKeyConstraint(
                ["draft_id"],
                ["classroom_planner_plan_drafts.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "draft_id",
                "student_id",
                name="uq_cp_student_seating_pref",
            ),
        )
        op.create_index(
            _DRAFT_SEATING_PREF_INDEX,
            _DRAFT_SEATING_PREF_TABLE,
            ["draft_id"],
            unique=False,
        )

    if _DRAFT_RELATIONSHIP_TABLE not in tables:
        op.create_table(
            _DRAFT_RELATIONSHIP_TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rule_id", sa.String(length=255), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column("student_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.ForeignKeyConstraint(
                ["draft_id"],
                ["classroom_planner_plan_drafts.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "draft_id",
                "rule_id",
                name="uq_cp_relationship_rule",
            ),
        )
        op.create_index(
            _DRAFT_RELATIONSHIP_INDEX,
            _DRAFT_RELATIONSHIP_TABLE,
            ["draft_id"],
            unique=False,
        )

    if _ROSTER_SEATING_PREF_TABLE in tables:
        roster_seating_indexes = {
            index["name"] for index in inspector.get_indexes(_ROSTER_SEATING_PREF_TABLE)
        }
        if _ROSTER_SEATING_PREF_INDEX in roster_seating_indexes:
            op.drop_index(_ROSTER_SEATING_PREF_INDEX, table_name=_ROSTER_SEATING_PREF_TABLE)
        op.drop_table(_ROSTER_SEATING_PREF_TABLE)

    if _ROSTER_RELATIONSHIP_TABLE in tables:
        roster_relationship_indexes = {
            index["name"] for index in inspector.get_indexes(_ROSTER_RELATIONSHIP_TABLE)
        }
        if _ROSTER_RELATIONSHIP_INDEX in roster_relationship_indexes:
            op.drop_index(_ROSTER_RELATIONSHIP_INDEX, table_name=_ROSTER_RELATIONSHIP_TABLE)
        op.drop_table(_ROSTER_RELATIONSHIP_TABLE)

    if _ROSTER_SMART_RULE_SET_TABLE in tables:
        op.drop_table(_ROSTER_SMART_RULE_SET_TABLE)
