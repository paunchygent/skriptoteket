from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_script_suggestions"
down_revision = "0002_catalog_taxonomy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "script_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("submitted_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("profession_slugs", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("category_slugs", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_script_suggestions_submitted_by_user_id", "script_suggestions", ["submitted_by_user_id"]
    )
    op.create_index("ix_script_suggestions_created_at", "script_suggestions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_script_suggestions_created_at", table_name="script_suggestions")
    op.drop_index(
        "ix_script_suggestions_submitted_by_user_id",
        table_name="script_suggestions",
    )
    op.drop_table("script_suggestions")
