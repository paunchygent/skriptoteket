"""Add grouping draft history columns

Revision ID: 4cb43fe0cf54
Revises: 91f6c4a7b2d1
Create Date: 2026-03-22 02:18:37.892382

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4cb43fe0cf54"
down_revision: Union[str, Sequence[str], None] = "91f6c4a7b2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("history_stack", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("undo_index", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        op.f("ix_classroom_planner_plan_drafts_draft_kind"),
        "classroom_planner_plan_drafts",
        ["draft_kind"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_classroom_planner_plan_drafts_draft_kind"),
        table_name="classroom_planner_plan_drafts",
    )
    op.drop_column("classroom_planner_plan_drafts", "undo_index")
    op.drop_column("classroom_planner_plan_drafts", "history_stack")
