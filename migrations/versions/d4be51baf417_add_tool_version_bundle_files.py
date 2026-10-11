"""Store a tool version's bundle files beside its entrypoint source.

Revision ID: d4be51baf417
Revises: a7d3e9c1f5b2
Create Date: 2026-10-11 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4be51baf417"
down_revision: str | Sequence[str] | None = "a7d3e9c1f5b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill every existing version as a single-file tool with no bundle files."""
    op.add_column(
        "tool_versions",
        sa.Column(
            "bundle_files",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Remove the bundle files column."""
    op.drop_column("tool_versions", "bundle_files")
