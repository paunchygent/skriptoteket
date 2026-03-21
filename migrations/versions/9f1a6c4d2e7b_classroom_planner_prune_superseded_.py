"""classroom planner prune superseded contracts

Revision ID: 9f1a6c4d2e7b
Revises: d8f0d0ef2b6d
Create Date: 2026-03-21 23:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9f1a6c4d2e7b"
down_revision: Union[str, Sequence[str], None] = "d8f0d0ef2b6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        "ix_classroom_planner_arrangement_snapshots_source_draft_id",
        table_name="classroom_planner_arrangement_snapshots",
    )
    op.drop_index(
        "ix_classroom_planner_arrangement_snapshots_owner_user_id",
        table_name="classroom_planner_arrangement_snapshots",
    )
    op.drop_table("classroom_planner_arrangement_snapshots")

    op.drop_index(
        "ix_classroom_planner_planning_profiles_draft_id",
        table_name="classroom_planner_planning_profiles",
    )
    op.drop_table("classroom_planner_planning_profiles")

    op.drop_index(
        "ix_classroom_planner_pair_constraints_draft_id",
        table_name="classroom_planner_pair_constraints",
    )
    op.drop_table("classroom_planner_pair_constraints")

    op.drop_column("classroom_planner_student_planning_meta", "independent_focus_support")
    op.drop_column("classroom_planner_plan_drafts", "engine_metadata")
    op.drop_column("classroom_planner_plan_drafts", "lesson_mode_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column(
            "lesson_mode_id",
            sa.String(length=255),
            server_default="group_work",
            nullable=False,
        ),
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column(
            "engine_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "classroom_planner_student_planning_meta",
        sa.Column("independent_focus_support", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "classroom_planner_pair_constraints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("student_id_a", sa.String(length=255), nullable=False),
        sa.Column("student_id_b", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=255), nullable=False),
        sa.Column("strength", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "draft_id",
            "student_id_a",
            "student_id_b",
            "kind",
            name="uq_cp_pair_constraint",
        ),
    )
    op.create_index(
        "ix_classroom_planner_pair_constraints_draft_id",
        "classroom_planner_pair_constraints",
        ["draft_id"],
        unique=False,
    )

    op.create_table(
        "classroom_planner_planning_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("profile_kind", sa.String(length=255), nullable=False),
        sa.Column("enable_student_meta", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "enable_pair_constraints", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "enable_zone_preferences", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column("enable_history_rules", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("teacher_proximity_weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("focus_support_weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("stability_weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("balance_weight", sa.Integer(), server_default="1", nullable=False),
        sa.Column("rotation_weight", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", name="uq_cp_planning_profile_draft"),
    )
    op.create_index(
        "ix_classroom_planner_planning_profiles_draft_id",
        "classroom_planner_planning_profiles",
        ["draft_id"],
        unique=False,
    )

    op.create_table(
        "classroom_planner_arrangement_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("source_draft_id", sa.UUID(), nullable=False),
        sa.Column("lesson_mode_id", sa.String(length=255), nullable=False),
        sa.Column("snapshot_schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_classroom_planner_arrangement_snapshots_owner_user_id",
        "classroom_planner_arrangement_snapshots",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_classroom_planner_arrangement_snapshots_source_draft_id",
        "classroom_planner_arrangement_snapshots",
        ["source_draft_id"],
        unique=False,
    )
