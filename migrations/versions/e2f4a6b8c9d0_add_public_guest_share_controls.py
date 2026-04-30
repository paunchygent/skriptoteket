"""add public guest share controls

Revision ID: e2f4a6b8c9d0
Revises: c7d9e3f5a1b2
Create Date: 2026-04-30 20:05:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2f4a6b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c7d9e3f5a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "classroom_planner_share_artifacts"


def upgrade() -> None:
    """Store browser-held public guest supersede/idempotency metadata."""

    op.add_column(
        _TABLE,
        sa.Column(
            "guest_snapshot_fingerprint",
            sa.String(length=96),
            nullable=True,
        ),
    )
    op.add_column(
        _TABLE,
        sa.Column("client_operation_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        _TABLE,
        sa.Column("revoke_secret_hash", sa.String(length=96), nullable=True),
    )
    op.create_index(
        "ix_cp_share_artifacts_public_client_op",
        _TABLE,
        ["source", "client_operation_id"],
        unique=True,
    )
    op.create_index(
        "ix_cp_share_artifacts_guest_fingerprint",
        _TABLE,
        ["source", "guest_snapshot_fingerprint", "revoked_at", "expires_at"],
    )


def downgrade() -> None:
    """Remove public guest supersede/idempotency metadata."""

    op.drop_index("ix_cp_share_artifacts_guest_fingerprint", table_name=_TABLE)
    op.drop_index("ix_cp_share_artifacts_public_client_op", table_name=_TABLE)
    op.drop_column(_TABLE, "revoke_secret_hash")
    op.drop_column(_TABLE, "client_operation_id")
    op.drop_column(_TABLE, "guest_snapshot_fingerprint")
