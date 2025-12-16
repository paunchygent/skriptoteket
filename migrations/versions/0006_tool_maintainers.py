from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_tool_maintainers"
down_revision = "0005_tool_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_maintainers",
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("tool_id", "user_id", name="pk_tool_maintainers"),
    )
    op.create_index("ix_tool_maintainers_tool_id", "tool_maintainers", ["tool_id"])
    op.create_index("ix_tool_maintainers_user_id", "tool_maintainers", ["user_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO tool_maintainers (tool_id, user_id)
            SELECT DISTINCT tool_id, created_by_user_id
            FROM tool_versions
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_tool_maintainers_user_id", table_name="tool_maintainers")
    op.drop_index("ix_tool_maintainers_tool_id", table_name="tool_maintainers")
    op.drop_table("tool_maintainers")
