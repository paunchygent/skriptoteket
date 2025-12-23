from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_tool_owner_user_id"
down_revision = "0011_tool_runs_input_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tools", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_tools_owner_user_id", "tools", ["owner_user_id"])
    op.create_foreign_key(
        "fk_tools_owner_user_id_users",
        "tools",
        "users",
        ["owner_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            """
            UPDATE tools t
            SET owner_user_id = s.submitted_by_user_id
            FROM script_suggestions s
            WHERE s.draft_tool_id = t.id
              AND t.owner_user_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tools t
            SET owner_user_id = s.submitted_by_user_id
            FROM script_suggestion_decisions d
            JOIN script_suggestions s ON s.id = d.suggestion_id
            WHERE d.created_tool_id = t.id
              AND t.owner_user_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tools t
            SET owner_user_id = v.created_by_user_id
            FROM (
                SELECT DISTINCT ON (tool_id) tool_id, created_by_user_id
                FROM tool_versions
                ORDER BY tool_id, version_number ASC, created_at ASC
            ) v
            WHERE v.tool_id = t.id
              AND t.owner_user_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE tools t
            SET owner_user_id = m.user_id
            FROM (
                SELECT DISTINCT ON (tool_id) tool_id, user_id
                FROM tool_maintainers
                ORDER BY tool_id, user_id ASC
            ) m
            WHERE m.tool_id = t.id
              AND t.owner_user_id IS NULL
            """
        )
    )

    op.alter_column("tools", "owner_user_id", nullable=False)

    op.execute(
        sa.text(
            """
            INSERT INTO tool_maintainers (tool_id, user_id)
            SELECT id, owner_user_id
            FROM tools
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_tools_owner_user_id_users", "tools", type_="foreignkey")
    op.drop_index("ix_tools_owner_user_id", table_name="tools")
    op.drop_column("tools", "owner_user_id")
