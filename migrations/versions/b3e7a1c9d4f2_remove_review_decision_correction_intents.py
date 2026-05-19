"""Remove Exam Converter review-decision correction state.

Revision ID: b3e7a1c9d4f2
Revises: 9b2f4c6d8e10
Create Date: 2026-05-20 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e7a1c9d4f2"
down_revision: str | None = "9b2f4c6d8e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Deactivate legacy export decisions and remove their conflict-family column."""

    op.execute(
        sa.text(
            """
            UPDATE exam_converter_correction_intents
            SET is_active = false,
                deactivated_at = COALESCE(deactivated_at, now()),
                updated_at = now()
            WHERE correction_kind = 'review_decision'
              AND is_active IS TRUE
            """
        )
    )
    op.drop_index(
        "uq_exam_conv_corr_intents_active_family",
        table_name="exam_converter_correction_intents",
    )
    op.drop_column("exam_converter_correction_intents", "conflict_family")


def downgrade() -> None:
    """Restore the dropped compatibility column for historical downgrades."""

    op.add_column(
        "exam_converter_correction_intents",
        sa.Column("conflict_family", sa.Text(), nullable=True),
    )
    op.create_index(
        "uq_exam_conv_corr_intents_active_family",
        "exam_converter_correction_intents",
        ["session_id", "conflict_family"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE AND conflict_family IS NOT NULL"),
    )
