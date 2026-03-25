"""add smart enabled to classroom planner drafts

Revision ID: e4b7c2d9a1f0
Revises: c9c1c9270a3d
Create Date: 2026-03-25 15:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4b7c2d9a1f0"
down_revision: Union[str, Sequence[str], None] = "c9c1c9270a3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "classroom_planner_plan_drafts",
        sa.Column("smart_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("classroom_planner_plan_drafts", "smart_enabled")
