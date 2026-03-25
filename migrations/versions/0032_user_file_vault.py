"""Add user vault files + usage tables.

Revision ID: 0032_user_file_vault
Revises: 0031_tool_runs_session_context
Create Date: 2026-01-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "0032_user_file_vault"
down_revision: str | None = "0031_tool_runs_session_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_has_index(*, inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "user_vault_files" not in tables:
        op.create_table(
            "user_vault_files",
            sa.Column("id", PGUUID(as_uuid=True), primary_key=True),
            sa.Column(
                "user_id",
                PGUUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("bytes", sa.BigInteger(), nullable=False),
            sa.Column("source_kind", sa.String(length=32), nullable=False),
            sa.Column(
                "source_run_id",
                PGUUID(as_uuid=True),
                sa.ForeignKey("tool_runs.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("source_artifact_id", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "user_vault_usage" not in tables:
        op.create_table(
            "user_vault_usage",
            sa.Column(
                "user_id",
                PGUUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column(
                "bytes_total",
                sa.BigInteger(),
                server_default="0",
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "user_vault_files" in tables:
        if not _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_user_id",
        ):
            op.create_index("ix_user_vault_files_user_id", "user_vault_files", ["user_id"])
        if not _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_deleted_at",
        ):
            op.create_index("ix_user_vault_files_deleted_at", "user_vault_files", ["deleted_at"])
        if not _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_source_run_id",
        ):
            op.create_index(
                "ix_user_vault_files_source_run_id", "user_vault_files", ["source_run_id"]
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if "user_vault_files" in tables:
        if _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_source_run_id",
        ):
            op.drop_index("ix_user_vault_files_source_run_id", table_name="user_vault_files")
        if _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_deleted_at",
        ):
            op.drop_index("ix_user_vault_files_deleted_at", table_name="user_vault_files")
        if _table_has_index(
            inspector=inspector,
            table_name="user_vault_files",
            index_name="ix_user_vault_files_user_id",
        ):
            op.drop_index("ix_user_vault_files_user_id", table_name="user_vault_files")
        op.drop_table("user_vault_files")

    if "user_vault_usage" in tables:
        op.drop_table("user_vault_usage")
