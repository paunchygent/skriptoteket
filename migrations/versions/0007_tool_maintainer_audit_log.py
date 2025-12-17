"""tool_maintainer_audit_log

Revision ID: 0007
Revises: 0006
Create Date: 2025-12-16 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_tool_maintainer_audit_log"
down_revision: Union[str, None] = "0006_tool_maintainers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tool_maintainer_audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tool_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("performed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "performed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["performed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tool_maintainer_audit_log_tool_id",
        "tool_maintainer_audit_log",
        ["tool_id"],
        unique=False,
    )
    op.create_index(
        "ix_tool_maintainer_audit_log_user_id",
        "tool_maintainer_audit_log",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tool_maintainer_audit_log_user_id", table_name="tool_maintainer_audit_log")
    op.drop_index("ix_tool_maintainer_audit_log_tool_id", table_name="tool_maintainer_audit_log")
    op.drop_table("tool_maintainer_audit_log")
