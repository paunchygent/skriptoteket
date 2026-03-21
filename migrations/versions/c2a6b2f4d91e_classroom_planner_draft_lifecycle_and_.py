"""classroom planner draft lifecycle and resume metadata

Revision ID: c2a6b2f4d91e
Revises: 8a1d4c7b32ef
Create Date: 2026-03-21 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2a6b2f4d91e"
down_revision: Union[str, Sequence[str], None] = "8a1d4c7b32ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column(
            "last_opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE classroom_planner_plan_drafts
        SET
            status = 'active',
            last_opened_at = COALESCE(updated_at, created_at, now())
        """
    )
    op.create_index(
        "ix_classroom_planner_plan_drafts_status",
        "classroom_planner_plan_drafts",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_classroom_planner_plan_drafts_status",
        table_name="classroom_planner_plan_drafts",
    )
    op.drop_column("classroom_planner_plan_drafts", "last_opened_at")
    op.drop_column("classroom_planner_plan_drafts", "status")
