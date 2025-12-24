from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0014_alembic_varchar64"
down_revision = "0013_user_profiles_and_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make idempotent: check current column length before altering
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c["name"]: c for c in inspector.get_columns("alembic_version")}
    version_col = columns.get("version_num")
    current_length = getattr(version_col["type"], "length", 32) if version_col else 32

    if current_length < 64:
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
