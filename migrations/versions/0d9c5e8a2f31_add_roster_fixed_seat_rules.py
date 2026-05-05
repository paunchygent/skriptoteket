"""Add roster-owned fixed-seat smart rules.

Purpose:
    Persist `Fast plats` rules as hard roster + classroom template +
    student + seat placements while keeping the existing roster smart-rule
    revision aggregate unchanged.

Relationships:
    - Depends on the current migration head so smart-rule children remain under
      `classroom_planner_roster_smart_rule_sets`.
    - The table is additive and can be dropped safely before shared data exists.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0d9c5e8a2f31"
down_revision: str | Sequence[str] | None = "f8a2c6d4e9b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "classroom_planner_roster_fixed_seat_rules"
_ROSTER_INDEX = "ix_classroom_planner_roster_fixed_seat_rules_roster_id"
_TEMPLATE_INDEX = "ix_classroom_planner_roster_fixed_seat_rules_template_id"


def upgrade() -> None:
    """Create the normalized fixed-seat smart-rule child table."""

    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=255), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column("seat_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["roster_id"],
            ["classroom_planner_roster_smart_rule_sets.roster_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["classroom_planner_room_templates.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("roster_id", "rule_id", name="uq_cp_roster_fixed_seat_rule"),
        sa.UniqueConstraint(
            "roster_id",
            "template_id",
            "student_id",
            name="uq_cp_roster_fixed_seat_student",
        ),
        sa.UniqueConstraint(
            "roster_id",
            "template_id",
            "seat_id",
            name="uq_cp_roster_fixed_seat_seat",
        ),
    )
    op.create_index(_ROSTER_INDEX, _TABLE, ["roster_id"], unique=False)
    op.create_index(_TEMPLATE_INDEX, _TABLE, ["template_id"], unique=False)


def downgrade() -> None:
    """Drop the additive fixed-seat smart-rule child table."""

    op.drop_index(_TEMPLATE_INDEX, table_name=_TABLE)
    op.drop_index(_ROSTER_INDEX, table_name=_TABLE)
    op.drop_table(_TABLE)
