"""Add classroom planner grouping export checkpoints.

Revision ID: 4d2c6b8e1a9f
Revises: 3e8b5c1a7d4f
Create Date: 2026-03-29 17:10:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4d2c6b8e1a9f"
down_revision = "3e8b5c1a7d4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "classroom_planner_grouping_export_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("roster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_export_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "grouping_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["roster_id"],
            ["classroom_planner_rosters.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["classroom_planner_room_templates.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_draft_id"],
            ["classroom_planner_plan_drafts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_export_job_id"],
            ["classroom_planner_grouping_export_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_roster_id"),
        "classroom_planner_grouping_export_checkpoints",
        ["roster_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_template_id"),
        "classroom_planner_grouping_export_checkpoints",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_source_draft_id"),
        "classroom_planner_grouping_export_checkpoints",
        ["source_draft_id"],
        unique=False,
    )
    op.create_index(
        "ix_cp_grouping_export_checkpoints_roster_created",
        "classroom_planner_grouping_export_checkpoints",
        ["roster_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_cp_grouping_export_checkpoints_source_job",
        "classroom_planner_grouping_export_checkpoints",
        ["source_export_job_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cp_grouping_export_checkpoints_source_job",
        table_name="classroom_planner_grouping_export_checkpoints",
    )
    op.drop_index(
        "ix_cp_grouping_export_checkpoints_roster_created",
        table_name="classroom_planner_grouping_export_checkpoints",
    )
    op.drop_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_source_draft_id"),
        table_name="classroom_planner_grouping_export_checkpoints",
    )
    op.drop_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_template_id"),
        table_name="classroom_planner_grouping_export_checkpoints",
    )
    op.drop_index(
        op.f("ix_classroom_planner_grouping_export_checkpoints_roster_id"),
        table_name="classroom_planner_grouping_export_checkpoints",
    )
    op.drop_table("classroom_planner_grouping_export_checkpoints")
