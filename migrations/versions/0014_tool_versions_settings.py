from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_tool_versions_settings"
down_revision = "0014_extend_alembic_version_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tool_versions",
        sa.Column("settings_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tool_versions", "settings_schema")
