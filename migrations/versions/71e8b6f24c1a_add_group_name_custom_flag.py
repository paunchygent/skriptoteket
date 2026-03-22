"""add group name custom flag

Revision ID: 71e8b6f24c1a
Revises: 4cb43fe0cf54
Create Date: 2026-03-22 11:05:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71e8b6f24c1a"
down_revision: Union[str, Sequence[str], None] = "4cb43fe0cf54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "classroom_planner_draft_groups",
        sa.Column("name_is_custom", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("classroom_planner_draft_groups", "name_is_custom")
