from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_curated_apps_runs"
down_revision = "0009_tool_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Curated apps (ADR-0023) need persisted runs/sessions without requiring a row in `tools`.
    op.drop_constraint("tool_sessions_tool_id_fkey", "tool_sessions", type_="foreignkey")
    op.drop_constraint("tool_runs_tool_id_fkey", "tool_runs", type_="foreignkey")

    op.alter_column(
        "tool_runs",
        "version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.add_column(
        "tool_runs",
        sa.Column(
            "source_kind",
            sa.String(length=32),
            nullable=False,
            server_default="tool_version",
        ),
    )
    op.add_column(
        "tool_runs",
        sa.Column("curated_app_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "tool_runs",
        sa.Column("curated_app_version", sa.String(length=128), nullable=True),
    )

    op.create_index("ix_tool_runs_source_kind", "tool_runs", ["source_kind"])
    op.create_index("ix_tool_runs_curated_app_id", "tool_runs", ["curated_app_id"])


def downgrade() -> None:
    op.drop_index("ix_tool_runs_curated_app_id", table_name="tool_runs")
    op.drop_index("ix_tool_runs_source_kind", table_name="tool_runs")

    op.drop_column("tool_runs", "curated_app_version")
    op.drop_column("tool_runs", "curated_app_id")
    op.drop_column("tool_runs", "source_kind")

    op.alter_column(
        "tool_runs",
        "version_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.create_foreign_key(
        "tool_runs_tool_id_fkey",
        "tool_runs",
        "tools",
        ["tool_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "tool_sessions_tool_id_fkey",
        "tool_sessions",
        "tools",
        ["tool_id"],
        ["id"],
        ondelete="CASCADE",
    )
