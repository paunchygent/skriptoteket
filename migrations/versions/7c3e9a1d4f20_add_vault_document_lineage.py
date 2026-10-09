"""Add document lineage and version to user vault files.

Revision ID: 7c3e9a1d4f20
Revises: a6d4e8f2c1b9
Create Date: 2026-10-09 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7c3e9a1d4f20"
down_revision: str | Sequence[str] | None = "a6d4e8f2c1b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add exam-workspace document lineage columns and the version uniqueness guard."""

    op.add_column(
        "user_vault_files",
        sa.Column("document_lineage_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "user_vault_files",
        sa.Column("document_version", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_user_vault_files_document_lineage_id",
        "user_vault_files",
        ["document_lineage_id"],
    )
    op.create_index(
        "uq_user_vault_files_document_version",
        "user_vault_files",
        ["user_id", "document_lineage_id", "document_version"],
        unique=True,
        postgresql_where=sa.text("document_lineage_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove exam-workspace document lineage columns."""

    op.drop_index("uq_user_vault_files_document_version", table_name="user_vault_files")
    op.drop_index("ix_user_vault_files_document_lineage_id", table_name="user_vault_files")
    op.drop_column("user_vault_files", "document_version")
    op.drop_column("user_vault_files", "document_lineage_id")
