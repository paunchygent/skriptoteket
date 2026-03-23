"""add room template grid dimensions

Revision ID: 9d7c4a12b6ef
Revises: 71e8b6f24c1a
Create Date: 2026-03-23 09:30:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9d7c4a12b6ef"
down_revision: Union[str, Sequence[str], None] = "71e8b6f24c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "classroom_planner_room_templates",
        sa.Column("grid_cols", sa.Integer(), nullable=False, server_default="14"),
    )
    op.add_column(
        "classroom_planner_room_templates",
        sa.Column("grid_rows", sa.Integer(), nullable=False, server_default="9"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("classroom_planner_room_templates", "grid_rows")
    op.drop_column("classroom_planner_room_templates", "grid_cols")
