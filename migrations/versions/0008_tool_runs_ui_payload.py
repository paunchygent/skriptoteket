from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008_tool_runs_ui_payload"
down_revision = "0007_tool_maintainer_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tool_runs", sa.Column("ui_payload", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tool_runs", "ui_payload")
