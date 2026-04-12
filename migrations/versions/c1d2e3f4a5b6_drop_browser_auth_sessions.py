"""Drop retired browser-auth sessions table.

Purpose:
    Remove Skriptoteket-owned browser session storage after HuleEdu becomes
    the browser session authority.

Relationships:
    - Follows the current migration head and removes the table initially
      created in `0001_init`.
    - Leaves `tool_sessions` untouched; those rows are app execution state,
      not browser-auth state.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "c1d2e3f4a5b6"
down_revision: str | Sequence[str] | None = "0f4c2d7a9b1e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "sessions"
_INDEXES = ("ix_sessions_expires_at", "ix_sessions_user_id")


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in set(inspector.get_table_names())


def _index_exists(*, table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    """Drop local browser-auth session storage.

    Existing session rows are intentionally discarded. They cannot be used
    after the PR-0253 hard break because browser authentication is proven by
    HuleEdu Gateway signed context instead of `skriptoteket_session`.
    """

    if not _table_exists(_TABLE):
        return

    for index_name in _INDEXES:
        if _index_exists(table_name=_TABLE, index_name=index_name):
            op.drop_index(index_name, table_name=_TABLE)

    op.drop_table(_TABLE)


def downgrade() -> None:
    """Recreate the empty legacy table shape for downgrade-only recovery."""

    if _table_exists(_TABLE):
        return

    op.create_table(
        _TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("csrf_token", sa.String(length=255), nullable=False),
        sa.Column("allow_remote_fallback", sa.Boolean(), nullable=True),
        sa.Column("inline_completion_provider", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_sessions_user_id", _TABLE, ["user_id"])
    op.create_index("ix_sessions_expires_at", _TABLE, ["expires_at"])
