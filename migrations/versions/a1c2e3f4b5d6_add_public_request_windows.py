"""add public request windows

Revision ID: a1c2e3f4b5d6
Revises: e8a3c5f1b7d2
Create Date: 2026-10-18 15:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c2e3f4b5d6"
down_revision: Union[str, Sequence[str], None] = "e8a3c5f1b7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "public_request_windows"


def upgrade() -> None:
    """Create the shared hourly public request counter table."""

    op.create_table(
        _TABLE,
        sa.Column("bucket", sa.String(length=32), nullable=False),
        sa.Column("caller_key", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("bucket", "caller_key", "window_start"),
    )
    op.create_index(
        "ix_public_request_windows_window_start",
        _TABLE,
        ["window_start"],
    )


def downgrade() -> None:
    """Drop the public request counter table."""

    op.drop_index("ix_public_request_windows_window_start", table_name=_TABLE)
    op.drop_table(_TABLE)
