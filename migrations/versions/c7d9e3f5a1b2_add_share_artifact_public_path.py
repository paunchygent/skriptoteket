"""add share artifact public path

Revision ID: c7d9e3f5a1b2
Revises: b4c6d8e1f2a3
Create Date: 2026-04-30 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d9e3f5a1b2"
down_revision: Union[str, Sequence[str], None] = "b4c6d8e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "classroom_planner_share_artifacts"


def upgrade() -> None:
    """Persist copyable public share paths for owner-scoped share lists."""

    op.add_column(_TABLE, sa.Column("public_path", sa.String(length=512), nullable=True))


def downgrade() -> None:
    """Remove persisted public share paths."""

    op.drop_column(_TABLE, "public_path")
