"""Add classroom planner smart profile preferences.

Revision ID: b6c9f2a1d4e8
Revises: f2a7c9d4e6b8
Create Date: 2026-05-09 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "b6c9f2a1d4e8"
down_revision = "f2a7c9d4e6b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("classroom_planner_smart_enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("classroom_planner_use_history", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "classroom_planner_grouping_seating_distance_enabled",
            sa.Boolean(),
            nullable=True,
        ),
    )
    op.alter_column(
        "classroom_planner_plan_drafts",
        "grouping_seating_distance_enabled",
        server_default=sa.false(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "classroom_planner_plan_drafts",
        "grouping_seating_distance_enabled",
        server_default=sa.true(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
    op.drop_column(
        "user_profiles",
        "classroom_planner_grouping_seating_distance_enabled",
    )
    op.drop_column("user_profiles", "classroom_planner_use_history")
    op.drop_column("user_profiles", "classroom_planner_smart_enabled")
