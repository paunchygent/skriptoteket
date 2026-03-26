"""Reset student smart preferences to seating-only teacher-distance rows.

This revision continues the burn-and-rebuild contract reset for the classroom
planner. The old smart-preference table exposed `support_seat`, which is no
longer the accepted product concept. The authoritative persistence contract is
now `classroom_planner_student_seating_preferences.near_teacher`.

Revision ID: 1d3e5f7a9b2c
Revises: 8c4d2e1f7a9b
Create Date: 2026-03-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "1d3e5f7a9b2c"
down_revision: str | Sequence[str] | None = "8c4d2e1f7a9b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_TABLE = "classroom_planner_student_smart_preferences"
_NEW_TABLE = "classroom_planner_student_seating_preferences"
_OLD_INDEX = "ix_classroom_planner_student_smart_preferences_draft_id"
_NEW_INDEX = "ix_classroom_planner_student_seating_preferences_draft_id"


def upgrade() -> None:
    """Replace the old smart-preference table with the seating-only contract."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _NEW_TABLE not in tables:
        op.create_table(
            _NEW_TABLE,
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
            _NEW_INDEX,
            _NEW_TABLE,
            ["draft_id"],
            unique=False,
        )

    if _OLD_TABLE in tables:
        old_indexes = {index["name"] for index in inspector.get_indexes(_OLD_TABLE)}
        if _OLD_INDEX in old_indexes:
            op.drop_index(_OLD_INDEX, table_name=_OLD_TABLE)
        op.drop_table(_OLD_TABLE)


def downgrade() -> None:
    """Restore the old smart-preference table and remove the seating-only one."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _OLD_TABLE not in tables:
        op.create_table(
            _OLD_TABLE,
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
            _OLD_INDEX,
            _OLD_TABLE,
            ["draft_id"],
            unique=False,
        )

    if _NEW_TABLE in tables:
        new_indexes = {index["name"] for index in inspector.get_indexes(_NEW_TABLE)}
        if _NEW_INDEX in new_indexes:
            op.drop_index(_NEW_INDEX, table_name=_NEW_TABLE)
        op.drop_table(_NEW_TABLE)
