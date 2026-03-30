"""Backfill the default Klassrumskartan bookmark for existing users.

Purpose:
    Seed the curated-app favorites table so current local users see
    Klassrumskartan as bookmarked by default, matching the registry default for
    newly registered users.

Relationships:
    - Depends on the current local migration head so `upgrade head` stays
      linear in this worktree.
    - Writes only to `user_favorite_apps` and remains idempotent via
      `ON CONFLICT DO NOTHING`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1e4d6c8b2f0"
down_revision: str | None = "8f3d2c1b4a6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_APP_ID = "classroom.group-seating-studio"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO user_favorite_apps (user_id, app_id)
            SELECT users.id, :app_id
            FROM users
            ON CONFLICT (user_id, app_id) DO NOTHING
            """
        ),
        {"app_id": _DEFAULT_APP_ID},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM user_favorite_apps WHERE app_id = :app_id"),
        {"app_id": _DEFAULT_APP_ID},
    )
