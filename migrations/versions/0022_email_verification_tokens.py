"""Add email_verification_tokens table.

Revision ID: 0022
Revises: 0021
Create Date: 2025-12-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "0022_email_verification_tokens"
down_revision: str | None = "0021_login_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "email_verification_tokens" not in tables:
        op.create_table(
            "email_verification_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("token", sa.String(64), unique=True, nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_email_verification_tokens_user_id",
            "email_verification_tokens",
            ["user_id"],
        )
        op.create_index(
            "ix_email_verification_tokens_token",
            "email_verification_tokens",
            ["token"],
        )
        op.create_index(
            "ix_email_verification_tokens_expires_at",
            "email_verification_tokens",
            ["expires_at"],
        )
    else:
        indexes = {index["name"] for index in inspector.get_indexes("email_verification_tokens")}
        if "ix_email_verification_tokens_user_id" not in indexes:
            op.create_index(
                "ix_email_verification_tokens_user_id",
                "email_verification_tokens",
                ["user_id"],
            )
        if "ix_email_verification_tokens_token" not in indexes:
            op.create_index(
                "ix_email_verification_tokens_token",
                "email_verification_tokens",
                ["token"],
            )
        if "ix_email_verification_tokens_expires_at" not in indexes:
            op.create_index(
                "ix_email_verification_tokens_expires_at",
                "email_verification_tokens",
                ["expires_at"],
            )


def downgrade() -> None:
    op.drop_index(
        "ix_email_verification_tokens_expires_at",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_token",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_user_id",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")
