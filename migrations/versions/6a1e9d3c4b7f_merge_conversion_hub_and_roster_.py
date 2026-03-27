"""Merge the Conversion Hub and roster-smart-rule migration heads.

This merge revision restores the repository's single-head Alembic invariant
after the Conversion Hub job ledger and roster-owned smart-rule boundary reset
landed from the same parent revision in the current worktree.

Revision ID: 6a1e9d3c4b7f
Revises: 2b6c4d8e1f9a, 5f2c7d1a9b8e
Create Date: 2026-03-27
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "6a1e9d3c4b7f"
down_revision: str | Sequence[str] | None = ("2b6c4d8e1f9a", "5f2c7d1a9b8e")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the two active heads without changing schema objects."""


def downgrade() -> None:
    """Unmerge the two active heads without changing schema objects."""
