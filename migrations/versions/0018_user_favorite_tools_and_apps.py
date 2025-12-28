"""Add user favorite tools and curated apps.

Revision ID: 0018
Revises: 0017
Create Date: 2025-12-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0018_user_favorite_tools_and_apps"
down_revision: str | None = "0017_tool_runs_input_values"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "user_favorite_tools" not in tables:
        op.create_table(
            "user_favorite_tools",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tool_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "tool_id", name="pk_user_favorite_tools"),
        )
        op.create_index("ix_user_favorite_tools_user_id", "user_favorite_tools", ["user_id"])
        op.create_index("ix_user_favorite_tools_tool_id", "user_favorite_tools", ["tool_id"])
    else:
        columns = {column["name"] for column in inspector.get_columns("user_favorite_tools")}
        if "created_at" not in columns:
            op.add_column(
                "user_favorite_tools",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )

        indexes = {index["name"] for index in inspector.get_indexes("user_favorite_tools")}
        if "ix_user_favorite_tools_user_id" not in indexes:
            op.create_index(
                "ix_user_favorite_tools_user_id",
                "user_favorite_tools",
                ["user_id"],
            )
        if "ix_user_favorite_tools_tool_id" not in indexes:
            op.create_index(
                "ix_user_favorite_tools_tool_id",
                "user_favorite_tools",
                ["tool_id"],
            )

    if "user_favorite_apps" not in tables:
        op.create_table(
            "user_favorite_apps",
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("app_id", sa.String(length=128), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "app_id", name="pk_user_favorite_apps"),
        )
        op.create_index("ix_user_favorite_apps_user_id", "user_favorite_apps", ["user_id"])
        op.create_index("ix_user_favorite_apps_app_id", "user_favorite_apps", ["app_id"])
    else:
        columns = {column["name"] for column in inspector.get_columns("user_favorite_apps")}
        if "created_at" not in columns:
            op.add_column(
                "user_favorite_apps",
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.func.now(),
                ),
            )

        indexes = {index["name"] for index in inspector.get_indexes("user_favorite_apps")}
        if "ix_user_favorite_apps_user_id" not in indexes:
            op.create_index(
                "ix_user_favorite_apps_user_id",
                "user_favorite_apps",
                ["user_id"],
            )
        if "ix_user_favorite_apps_app_id" not in indexes:
            op.create_index(
                "ix_user_favorite_apps_app_id",
                "user_favorite_apps",
                ["app_id"],
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "user_favorite_apps" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("user_favorite_apps")}
        if "ix_user_favorite_apps_app_id" in indexes:
            op.drop_index("ix_user_favorite_apps_app_id", table_name="user_favorite_apps")
        if "ix_user_favorite_apps_user_id" in indexes:
            op.drop_index("ix_user_favorite_apps_user_id", table_name="user_favorite_apps")
        op.drop_table("user_favorite_apps")

    if "user_favorite_tools" in tables:
        indexes = {index["name"] for index in inspector.get_indexes("user_favorite_tools")}
        if "ix_user_favorite_tools_tool_id" in indexes:
            op.drop_index("ix_user_favorite_tools_tool_id", table_name="user_favorite_tools")
        if "ix_user_favorite_tools_user_id" in indexes:
            op.drop_index("ix_user_favorite_tools_user_id", table_name="user_favorite_tools")
        op.drop_table("user_favorite_tools")
