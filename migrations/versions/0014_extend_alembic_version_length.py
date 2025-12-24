from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_extend_alembic_version_length"
down_revision = "0013_user_profiles_and_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "alembic_version",
        "version_num",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    # Keep the wider length to avoid truncation on downgrade.
    pass
