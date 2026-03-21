"""classroom planner slice 2 workspace and snapshots

Revision ID: 8a1d4c7b32ef
Revises: 4f5605f8be18
Create Date: 2026-03-20 23:45:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8a1d4c7b32ef"
down_revision: Union[str, Sequence[str], None] = "4f5605f8be18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "classroom_planner_room_templates",
        sa.Column(
            "fixtures",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
    op.create_table(
        "classroom_planner_draft_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "group_id", name="uq_cp_draft_group_id"),
    )
    op.create_index(
        "ix_classroom_planner_draft_groups_draft_id",
        "classroom_planner_draft_groups",
        ["draft_id"],
        unique=False,
    )
    op.create_table(
        "classroom_planner_student_planning_meta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.String(length=255), nullable=False),
        sa.Column("teacher_proximity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("independent_focus_support", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stability_preference", sa.Integer(), server_default="0", nullable=False),
        sa.Column("preferred_zone", sa.String(length=255), nullable=True),
        sa.Column("avoid_zone", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("draft_id", "student_id", name="uq_cp_student_meta"),
    )
    op.create_index(
        "ix_classroom_planner_student_planning_meta_draft_id",
        "classroom_planner_student_planning_meta",
        ["draft_id"],
        unique=False,
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

    op.execute(
        """
        INSERT INTO classroom_planner_draft_groups (draft_id, group_id, name, sort_order)
        SELECT
            d.id,
            CONCAT('group-', gs.idx, '-', LEFT(REPLACE(d.id::text, '-', ''), 8)),
            CONCAT('Grupp ', gs.idx),
            gs.idx - 1
        FROM classroom_planner_plan_drafts AS d
        CROSS JOIN LATERAL generate_series(1, d.group_count) AS gs(idx)
        """
    )

    op.execute(
        """
        UPDATE classroom_planner_group_assignments AS ga
        SET group_id = CONCAT(
            'group-',
            SUBSTRING(ga.group_id FROM '[0-9]+'),
            '-',
            LEFT(REPLACE(ga.draft_id::text, '-', ''), 8)
        )
        WHERE ga.group_id ~ 'group-[0-9]+'
        """
    )

    op.create_unique_constraint(
        "uq_cp_group_assignment",
        "classroom_planner_group_assignments",
        ["draft_id", "student_id"],
    )
    op.create_unique_constraint(
        "uq_cp_seat_assignment_student",
        "classroom_planner_seat_assignments",
        ["draft_id", "student_id"],
    )
    op.create_unique_constraint(
        "uq_cp_seat_assignment_seat",
        "classroom_planner_seat_assignments",
        ["draft_id", "seat_id"],
    )
    op.drop_column("classroom_planner_plan_drafts", "group_count")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("group_count", sa.Integer(), server_default="6", nullable=False),
    )
    op.execute(
        """
        UPDATE classroom_planner_plan_drafts AS d
        SET group_count = COALESCE(group_counts.count, 6)
        FROM (
            SELECT draft_id, COUNT(*) AS count
            FROM classroom_planner_draft_groups
            GROUP BY draft_id
        ) AS group_counts
        WHERE d.id = group_counts.draft_id
        """
    )
    op.drop_constraint(
        "uq_cp_seat_assignment_seat",
        "classroom_planner_seat_assignments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_cp_seat_assignment_student",
        "classroom_planner_seat_assignments",
        type_="unique",
    )
    op.drop_constraint(
        "uq_cp_group_assignment",
        "classroom_planner_group_assignments",
        type_="unique",
    )
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
    op.drop_index(
        "ix_classroom_planner_student_planning_meta_draft_id",
        table_name="classroom_planner_student_planning_meta",
    )
    op.drop_table("classroom_planner_student_planning_meta")
    op.drop_index(
        "ix_classroom_planner_draft_groups_draft_id",
        table_name="classroom_planner_draft_groups",
    )
    op.drop_table("classroom_planner_draft_groups")
    op.drop_column("classroom_planner_plan_drafts", "engine_metadata")
    op.drop_column("classroom_planner_room_templates", "fixtures")
