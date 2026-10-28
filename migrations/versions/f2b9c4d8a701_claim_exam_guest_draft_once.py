"""Claim guest exam drafts by draft ID alone.

Revision ID: f2b9c4d8a701
Revises: aa30c309b36c
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f2b9c4d8a701"
down_revision: str | Sequence[str] | None = "aa30c309b36c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace development claims with a globally unique draft key."""
    op.execute("DELETE FROM exam_guest_draft_handoffs")
    op.drop_constraint(
        "exam_guest_draft_handoffs_pkey", "exam_guest_draft_handoffs", type_="primary"
    )
    op.create_primary_key(
        "exam_guest_draft_handoffs_pkey", "exam_guest_draft_handoffs", ["draft_id"]
    )


def downgrade() -> None:
    """Restore the previous composite key."""
    op.drop_constraint(
        "exam_guest_draft_handoffs_pkey", "exam_guest_draft_handoffs", type_="primary"
    )
    op.create_primary_key(
        "exam_guest_draft_handoffs_pkey", "exam_guest_draft_handoffs", ["owner_user_id", "draft_id"]
    )
