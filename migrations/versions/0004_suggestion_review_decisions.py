from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_suggestion_review_decisions"
down_revision = "0003_script_suggestions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tools",
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_tools_is_published", "tools", ["is_published"])

    op.add_column(
        "script_suggestions",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending_review"),
    )
    op.add_column(
        "script_suggestions",
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "script_suggestions",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("script_suggestions", sa.Column("review_rationale", sa.Text(), nullable=True))
    op.add_column(
        "script_suggestions",
        sa.Column("draft_tool_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_script_suggestions_status", "script_suggestions", ["status"])
    op.create_index(
        "ix_script_suggestions_reviewed_by_user_id", "script_suggestions", ["reviewed_by_user_id"]
    )
    op.create_index("ix_script_suggestions_reviewed_at", "script_suggestions", ["reviewed_at"])
    op.create_foreign_key(
        "fk_script_suggestions_reviewed_by_user_id_users",
        "script_suggestions",
        "users",
        ["reviewed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_script_suggestions_draft_tool_id_tools",
        "script_suggestions",
        "tools",
        ["draft_tool_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "script_suggestion_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suggestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("profession_slugs", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("category_slugs", postgresql.ARRAY(sa.String(length=64)), nullable=False),
        sa.Column("created_tool_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["suggestion_id"], ["script_suggestions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_tool_id"], ["tools.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_script_suggestion_decisions_suggestion_id",
        "script_suggestion_decisions",
        ["suggestion_id"],
    )
    op.create_index(
        "ix_script_suggestion_decisions_decided_at",
        "script_suggestion_decisions",
        ["decided_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_script_suggestion_decisions_decided_at", table_name="script_suggestion_decisions"
    )
    op.drop_index(
        "ix_script_suggestion_decisions_suggestion_id", table_name="script_suggestion_decisions"
    )
    op.drop_table("script_suggestion_decisions")

    op.drop_constraint(
        "fk_script_suggestions_draft_tool_id_tools",
        "script_suggestions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_script_suggestions_reviewed_by_user_id_users",
        "script_suggestions",
        type_="foreignkey",
    )
    op.drop_index("ix_script_suggestions_reviewed_at", table_name="script_suggestions")
    op.drop_index("ix_script_suggestions_reviewed_by_user_id", table_name="script_suggestions")
    op.drop_index("ix_script_suggestions_status", table_name="script_suggestions")
    op.drop_column("script_suggestions", "draft_tool_id")
    op.drop_column("script_suggestions", "review_rationale")
    op.drop_column("script_suggestions", "reviewed_at")
    op.drop_column("script_suggestions", "reviewed_by_user_id")
    op.drop_column("script_suggestions", "status")

    op.drop_index("ix_tools_is_published", table_name="tools")
    op.drop_column("tools", "is_published")
