"""Remove the answer-key daily token lease; track the door limit on enrichment jobs.

Domain purpose: the local Postgres token ledger for answer-key provider
calls is gone (TASK-SKRIPT-41-01-03): the ``exam_answer_key_token_leases``
table and its two indexes are dropped. The execution-worker enrichment job
ledger gains a nullable ``ai_limit`` column naming the HuleEdu door limit
(``AiDailyLimit``) that refused the job, so the status surface can show the
limit note.

Revision ID: 9f3c7a1b4e02
Revises: 015a3af12871
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9f3c7a1b4e02"
down_revision: str | Sequence[str] | None = "015a3af12871"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop the token-lease table and add the enrichment-job door limit."""

    op.execute("DROP INDEX IF EXISTS ix_exam_answer_key_token_leases_job_id")
    op.execute("DROP INDEX IF EXISTS ix_exam_answer_key_token_leases_day")
    op.execute("DROP TABLE IF EXISTS exam_answer_key_token_leases")
    op.execute(
        "ALTER TABLE exam_answer_key_enrichment_jobs ADD COLUMN IF NOT EXISTS ai_limit VARCHAR(32)"
    )


def downgrade() -> None:
    """Recreate the token-lease table exactly as b7d3f1a5c9e2; drop ai_limit."""

    op.create_table(
        "exam_answer_key_token_leases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("utc_day", sa.Date(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", sa.String(length=64), nullable=False),
        sa.Column("provider_profile_id", sa.String(length=128), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("actual_tokens", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_exam_answer_key_token_leases_day",
        "exam_answer_key_token_leases",
        ["utc_day"],
    )
    op.create_index(
        "ix_exam_answer_key_token_leases_job_id",
        "exam_answer_key_token_leases",
        ["job_id"],
    )
    op.execute("ALTER TABLE exam_answer_key_enrichment_jobs DROP COLUMN IF EXISTS ai_limit")
