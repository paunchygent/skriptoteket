"""Add missing classroom planner smart preference and rule tables.

The planner draft ORM now carries per-student smart preferences and explicit
relationship rules. Those child tables must exist for `selectin` draft loading
to work on live routes such as resumable-draft lookups and workspace loads.

Revision ID: 8c4d2e1f7a9b
Revises: 7b8a6f1d2c3e
Create Date: 2026-03-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "8c4d2e1f7a9b"
down_revision: str | Sequence[str] | None = "7b8a6f1d2c3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_META_TABLE = "classroom_planner_student_planning_meta"
_LEGACY_META_COLUMNS = (
    "teacher_proximity",
    "stability_preference",
    "preferred_zone",
    "avoid_zone",
)


def upgrade() -> None:
    """Create the missing planner child tables used by live draft loading."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if "classroom_planner_student_smart_preferences" not in tables:
        op.create_table(
            "classroom_planner_student_smart_preferences",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("student_id", sa.String(length=255), nullable=False),
            sa.Column(
                "support_seat",
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
                name="uq_cp_student_smart_pref",
            ),
        )
        op.create_index(
            "ix_classroom_planner_student_smart_preferences_draft_id",
            "classroom_planner_student_smart_preferences",
            ["draft_id"],
            unique=False,
        )

    if "classroom_planner_relationship_rules" not in tables:
        op.create_table(
            "classroom_planner_relationship_rules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("rule_id", sa.String(length=255), nullable=False),
            sa.Column("kind", sa.String(length=32), nullable=False),
            sa.Column(
                "student_ids",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
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
            "ix_classroom_planner_relationship_rules_draft_id",
            "classroom_planner_relationship_rules",
            ["draft_id"],
            unique=False,
        )

    if _LEGACY_META_TABLE in tables:
        legacy_columns = {column["name"] for column in inspector.get_columns(_LEGACY_META_TABLE)}
        for column_name in _LEGACY_META_COLUMNS:
            if column_name in legacy_columns:
                op.drop_column(_LEGACY_META_TABLE, column_name)


def downgrade() -> None:
    """Drop the planner smart-preference and relationship-rule tables."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _LEGACY_META_TABLE in tables:
        legacy_columns = {column["name"] for column in inspector.get_columns(_LEGACY_META_TABLE)}
        if "teacher_proximity" not in legacy_columns:
            op.add_column(
                _LEGACY_META_TABLE,
                sa.Column(
                    "teacher_proximity",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if "stability_preference" not in legacy_columns:
            op.add_column(
                _LEGACY_META_TABLE,
                sa.Column(
                    "stability_preference",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("0"),
                ),
            )
        if "preferred_zone" not in legacy_columns:
            op.add_column(
                _LEGACY_META_TABLE,
                sa.Column("preferred_zone", sa.String(length=255), nullable=True),
            )
        if "avoid_zone" not in legacy_columns:
            op.add_column(
                _LEGACY_META_TABLE,
                sa.Column("avoid_zone", sa.String(length=255), nullable=True),
            )

    if "classroom_planner_relationship_rules" in tables:
        op.drop_index(
            "ix_classroom_planner_relationship_rules_draft_id",
            table_name="classroom_planner_relationship_rules",
        )
        op.drop_table("classroom_planner_relationship_rules")

    if "classroom_planner_student_smart_preferences" in tables:
        op.drop_index(
            "ix_classroom_planner_student_smart_preferences_draft_id",
            table_name="classroom_planner_student_smart_preferences",
        )
        op.drop_table("classroom_planner_student_smart_preferences")
