"""Add login_events table.

Revision ID: 0021
Revises: 0020
Create Date: 2025-12-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0021_login_events"
down_revision: str | None = "0020_sandbox_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "login_events" not in tables:
        op.create_table(
            "login_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("failure_code", sa.String(64), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("auth_provider", sa.String(32), nullable=False),
            sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("geo_country_code", sa.String(8), nullable=True),
            sa.Column("geo_region", sa.String(128), nullable=True),
            sa.Column("geo_city", sa.String(128), nullable=True),
            sa.Column("geo_latitude", sa.Float(), nullable=True),
            sa.Column("geo_longitude", sa.Float(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_login_events_user_id", "login_events", ["user_id"])
        op.create_index("ix_login_events_created_at", "login_events", ["created_at"])
        op.create_index("ix_login_events_status", "login_events", ["status"])
    else:
        indexes = {index["name"] for index in inspector.get_indexes("login_events")}
        if "ix_login_events_user_id" not in indexes:
            op.create_index("ix_login_events_user_id", "login_events", ["user_id"])
        if "ix_login_events_created_at" not in indexes:
            op.create_index("ix_login_events_created_at", "login_events", ["created_at"])
        if "ix_login_events_status" not in indexes:
            op.create_index("ix_login_events_status", "login_events", ["status"])


def downgrade() -> None:
    op.drop_index("ix_login_events_status", table_name="login_events")
    op.drop_index("ix_login_events_created_at", table_name="login_events")
    op.drop_index("ix_login_events_user_id", table_name="login_events")
    op.drop_table("login_events")
