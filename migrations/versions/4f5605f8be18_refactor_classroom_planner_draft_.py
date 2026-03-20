"""refactor classroom planner draft assignments

Revision ID: 4f5605f8be18
Revises: f30ac060991c
Create Date: 2026-03-20 22:06:10.871327

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4f5605f8be18"
down_revision: Union[str, Sequence[str], None] = "f30ac060991c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "classroom_planner_group_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column("group_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classroom_planner_group_assignments_draft_id"),
        "classroom_planner_group_assignments",
        ["draft_id"],
        unique=False,
    )
    op.create_table(
        "classroom_planner_seat_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column("seat_id", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classroom_planner_seat_assignments_draft_id"),
        "classroom_planner_seat_assignments",
        ["draft_id"],
        unique=False,
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("group_count", sa.Integer(), server_default="6", nullable=False),
    )
    op.drop_column("classroom_planner_plan_drafts", "seat_assignments")
    op.drop_column("classroom_planner_plan_drafts", "group_assignments")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column(
            "group_assignments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column(
            "seat_assignments",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_column("classroom_planner_plan_drafts", "group_count")
    op.drop_column("classroom_planner_plan_drafts", "revision")
    op.drop_index(
        op.f("ix_classroom_planner_seat_assignments_draft_id"),
        table_name="classroom_planner_seat_assignments",
    )
    op.drop_table("classroom_planner_seat_assignments")
    op.drop_index(
        op.f("ix_classroom_planner_group_assignments_draft_id"),
        table_name="classroom_planner_group_assignments",
    )
    op.drop_table("classroom_planner_group_assignments")
