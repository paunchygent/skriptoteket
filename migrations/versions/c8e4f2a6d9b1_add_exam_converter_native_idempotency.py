"""Add native Exam Converter submission and retry identities."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e4f2a6d9b1"
down_revision: str | Sequence[str] | None = "b7d3f1a5c9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversion_hub_jobs",
        sa.Column("submission_idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_conversion_hub_jobs_owner_submission_key",
        "conversion_hub_jobs",
        ["owner_user_id", "submission_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("submission_idempotency_key IS NOT NULL"),
    )
    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("retry_identity", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exam_answer_key_enrichment_jobs", "retry_identity")
    op.drop_index(
        "uq_conversion_hub_jobs_owner_submission_key",
        table_name="conversion_hub_jobs",
    )
    op.drop_column("conversion_hub_jobs", "submission_idempotency_key")
