"""add classroom planner share preview assets

Revision ID: f8a2c6d4e9b1
Revises: e2f4a6b8c9d0
Create Date: 2026-05-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a2c6d4e9b1"
down_revision: str | Sequence[str] | None = "e2f4a6b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "classroom_planner_share_preview_assets"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column(
            "share_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("classroom_planner_share_artifacts.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("image_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("preview_content_hash", sa.String(length=96), nullable=False),
        sa.Column("source_content_hash", sa.String(length=96), nullable=False),
        sa.Column("presentation_hash", sa.String(length=96), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_cp_share_preview_assets_source_hash",
        _TABLE,
        ["source_content_hash"],
    )
    op.create_index(
        "ix_cp_share_preview_assets_preview_hash",
        _TABLE,
        ["preview_content_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_cp_share_preview_assets_preview_hash", table_name=_TABLE)
    op.drop_index("ix_cp_share_preview_assets_source_hash", table_name=_TABLE)
    op.drop_table(_TABLE)
