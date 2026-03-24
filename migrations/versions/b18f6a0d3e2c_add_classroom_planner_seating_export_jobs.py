"""add classroom planner seating export jobs

Revision ID: b18f6a0d3e2c
Revises: 9d7c4a12b6ef
Create Date: 2026-03-24 15:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b18f6a0d3e2c"
down_revision: Union[str, Sequence[str], None] = "9d7c4a12b6ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "classroom_planner_seating_export_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("draft_id", sa.UUID(), nullable=False),
        sa.Column("roster_id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("export_kind", sa.String(length=32), nullable=False),
        sa.Column("layout_id", sa.String(length=64), nullable=False),
        sa.Column("paper_size", sa.String(length=32), nullable=False),
        sa.Column("output_filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("upstream_job_id", sa.String(length=255), nullable=True),
        sa.Column("webhook_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("webhook_secret", sa.String(length=255), nullable=True),
        sa.Column("vault_file_id", sa.UUID(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"], ["classroom_planner_plan_drafts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vault_file_id"], ["user_vault_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cp_seating_export_jobs_owner_created",
        "classroom_planner_seating_export_jobs",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cp_seating_export_jobs_owner_user_id",
        "classroom_planner_seating_export_jobs",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_cp_seating_export_jobs_draft_id",
        "classroom_planner_seating_export_jobs",
        ["draft_id"],
        unique=False,
    )
    op.create_index(
        "ix_cp_seating_export_jobs_status",
        "classroom_planner_seating_export_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_cp_seating_export_jobs_upstream",
        "classroom_planner_seating_export_jobs",
        ["upstream_job_id"],
        unique=True,
        postgresql_where=sa.text("upstream_job_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "uq_cp_seating_export_jobs_upstream",
        table_name="classroom_planner_seating_export_jobs",
        postgresql_where=sa.text("upstream_job_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_cp_seating_export_jobs_status",
        table_name="classroom_planner_seating_export_jobs",
    )
    op.drop_index(
        "ix_cp_seating_export_jobs_draft_id",
        table_name="classroom_planner_seating_export_jobs",
    )
    op.drop_index(
        "ix_cp_seating_export_jobs_owner_user_id",
        table_name="classroom_planner_seating_export_jobs",
    )
    op.drop_index(
        "ix_cp_seating_export_jobs_owner_created",
        table_name="classroom_planner_seating_export_jobs",
    )
    op.drop_table("classroom_planner_seating_export_jobs")
