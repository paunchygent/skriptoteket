"""Store a sandbox snapshot's bundle files beside its entrypoint source.

Revision ID: e3b7a1c5d9f2
Revises: d4be51baf417
Create Date: 2026-10-11 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3b7a1c5d9f2"
down_revision: str | Sequence[str] | None = "d4be51baf417"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill every existing snapshot as a single-file tool with no bundle files."""
    op.add_column(
        "sandbox_snapshots",
        sa.Column(
            "bundle_files",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    """Remove the bundle files column."""
    op.drop_column("sandbox_snapshots", "bundle_files")
