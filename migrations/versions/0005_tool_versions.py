from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005_tool_versions"
down_revision = "0004_suggestion_review_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("entrypoint", sa.String(length=128), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("derived_from_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "submitted_for_review_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("submitted_for_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["derived_from_version_id"],
            ["tool_versions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["submitted_for_review_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["published_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "tool_id",
            "version_number",
            name="uq_tool_versions_tool_id_version_number",
        ),
    )
    op.create_index("ix_tool_versions_tool_id", "tool_versions", ["tool_id"])
    op.create_index("ix_tool_versions_state", "tool_versions", ["state"])
    op.create_index("ix_tool_versions_created_at", "tool_versions", ["created_at"])
    op.create_index(
        "ix_tool_versions_tool_id_content_hash",
        "tool_versions",
        ["tool_id", "content_hash"],
    )
    op.create_index(
        "ux_tool_versions_one_active_per_tool",
        "tool_versions",
        ["tool_id"],
        unique=True,
        postgresql_where=sa.text("state = 'active'"),
    )

    op.create_table(
        "tool_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context", sa.String(length=16), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workdir_path", sa.Text(), nullable=False),
        sa.Column("input_filename", sa.String(length=255), nullable=False),
        sa.Column("input_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("html_output", sa.Text(), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column(
            "artifacts_manifest",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["tool_versions.id"]),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_tool_runs_tool_id", "tool_runs", ["tool_id"])
    op.create_index("ix_tool_runs_version_id", "tool_runs", ["version_id"])
    op.create_index("ix_tool_runs_context", "tool_runs", ["context"])
    op.create_index("ix_tool_runs_requested_by_user_id", "tool_runs", ["requested_by_user_id"])
    op.create_index("ix_tool_runs_status", "tool_runs", ["status"])
    op.create_index("ix_tool_runs_started_at", "tool_runs", ["started_at"])

    op.add_column(
        "tools", sa.Column("active_version_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_tools_active_version_id", "tools", ["active_version_id"])
    op.create_foreign_key(
        "fk_tools_active_version_id_tool_versions",
        "tools",
        "tool_versions",
        ["active_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_tools_active_version_id_tool_versions", "tools", type_="foreignkey")
    op.drop_index("ix_tools_active_version_id", table_name="tools")
    op.drop_column("tools", "active_version_id")

    op.drop_index("ix_tool_runs_started_at", table_name="tool_runs")
    op.drop_index("ix_tool_runs_status", table_name="tool_runs")
    op.drop_index("ix_tool_runs_requested_by_user_id", table_name="tool_runs")
    op.drop_index("ix_tool_runs_context", table_name="tool_runs")
    op.drop_index("ix_tool_runs_version_id", table_name="tool_runs")
    op.drop_index("ix_tool_runs_tool_id", table_name="tool_runs")
    op.drop_table("tool_runs")

    op.drop_index("ux_tool_versions_one_active_per_tool", table_name="tool_versions")
    op.drop_index("ix_tool_versions_tool_id_content_hash", table_name="tool_versions")
    op.drop_index("ix_tool_versions_created_at", table_name="tool_versions")
    op.drop_index("ix_tool_versions_state", table_name="tool_versions")
    op.drop_index("ix_tool_versions_tool_id", table_name="tool_versions")
    op.drop_table("tool_versions")
