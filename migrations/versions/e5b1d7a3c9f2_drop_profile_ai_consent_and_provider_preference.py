"""Drop the remote-fallback consent and inline-completion provider preference.

Domain purpose: script-editor AI no longer asks the teacher for remote-provider
consent or a local/external inline-completion choice (TASK-SKRIPT-41-01-02).
Both profile preference columns are removed from ``user_profiles``. The
``sessions`` table that cached them was already dropped by ``c1d2e3f4a5b6``.

Revision ID: e5b1d7a3c9f2
Revises: 9f3c7a1b4e02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e5b1d7a3c9f2"
down_revision: str | Sequence[str] | None = "9f3c7a1b4e02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop both preference columns from ``user_profiles`` when present."""

    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS allow_remote_fallback")
    op.execute("ALTER TABLE user_profiles DROP COLUMN IF EXISTS inline_completion_provider")


def downgrade() -> None:
    """Re-add both columns as nullable, with their original types."""

    op.execute("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS allow_remote_fallback BOOLEAN")
    op.execute(
        "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS inline_completion_provider VARCHAR(16)"
    )
