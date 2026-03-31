"""Drop the superseded classroom planner student notes table.

Purpose:
    Remove the draft-scoped student notes persistence that used to back the
    Klassrumskartan seating drawer. Regler now owns the supported rule-editing
    surface, so the old notes table and its leftover history payload keys
    should disappear from the active schema.

Relationships:
    - Depends on the current migration head so `upgrade head` stays linear.
    - Cleans `classroom_planner_plan_drafts.history_stack` so existing draft
      history snapshots stop carrying the retired `student_planning_meta` key.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "b7f9c2d4e1a6"
down_revision: str | Sequence[str] | None = "a1e4d6c8b2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TABLE = "classroom_planner_student_planning_meta"
_LEGACY_INDEX = "ix_classroom_planner_student_planning_meta_draft_id"


def _drop_history_meta_key() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE classroom_planner_plan_drafts
            SET history_stack = (
                SELECT COALESCE(
                    jsonb_agg(CASE
                        WHEN jsonb_typeof(snapshot) = 'object'
                        THEN snapshot - 'student_planning_meta'
                        ELSE snapshot
                    END),
                    '[]'::jsonb
                )
                FROM jsonb_array_elements(history_stack) AS snapshot
            )
            WHERE history_stack IS NOT NULL
              AND jsonb_typeof(history_stack) = 'array'
            """
        )
    )


def upgrade() -> None:
    """Drop the retired draft-scoped notes table and scrub history payloads."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    _drop_history_meta_key()

    if _LEGACY_TABLE not in tables:
        return

    index_names = {index["name"] for index in inspector.get_indexes(_LEGACY_TABLE)}
    if _LEGACY_INDEX in index_names:
        op.drop_index(_LEGACY_INDEX, table_name=_LEGACY_TABLE)
    op.drop_table(_LEGACY_TABLE)


def downgrade() -> None:
    """Recreate the retired notes table for downgrade compatibility."""

    connection = op.get_bind()
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())

    if _LEGACY_TABLE in tables:
        return

    op.create_table(
        _LEGACY_TABLE,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["classroom_planner_plan_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "student_id", name="uq_cp_student_meta"),
    )
    op.create_index(_LEGACY_INDEX, _LEGACY_TABLE, ["draft_id"], unique=False)
