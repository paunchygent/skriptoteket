from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0014_tool_versions_settings"
down_revision = "0014_alembic_varchar64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make idempotent: check if column exists before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c["name"] for c in inspector.get_columns("tool_versions")}

    if "settings_schema" not in columns:
        op.add_column(
            "tool_versions",
            sa.Column("settings_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("tool_versions", "settings_schema")
