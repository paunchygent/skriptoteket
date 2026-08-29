"""Add the exam answer-key enrichment vertical tables.

Domain purpose: Stand up the ST-SKRIPT-39-02 machine answer-key completion
lane: the single Postgres daily token-lease table (UTC-day partitioned,
never refunded), the execution-worker enrichment job ledger, and the
machine-proposed overlay proposal records.

Relationships: enrichment jobs bind one-to-one to `conversion_hub_jobs`;
proposed overlays bind one-to-one to enrichment jobs.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d3f1a5c9e2"
down_revision: str | Sequence[str] | None = "f4c8e2a6b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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

    op.create_table(
        "exam_answer_key_enrichment_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversion_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input_filename", sa.String(length=255), nullable=False),
        sa.Column("source_dxe", sa.LargeBinary(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["conversion_job_id"],
            ["conversion_hub_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "conversion_job_id",
            name="uq_exam_answer_key_enrichment_jobs_conversion_job_id",
        ),
    )
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_conversion_job_id",
        "exam_answer_key_enrichment_jobs",
        ["conversion_job_id"],
    )
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_owner_user_id",
        "exam_answer_key_enrichment_jobs",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_status",
        "exam_answer_key_enrichment_jobs",
        ["status"],
    )
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_claim",
        "exam_answer_key_enrichment_jobs",
        ["status", "available_at"],
    )

    op.create_table(
        "exam_answer_key_proposed_overlays",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enrichment_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_file_sha256", sa.String(length=128), nullable=False),
        sa.Column("source_ir_sha256", sa.String(length=128), nullable=False),
        sa.Column("provider_profile_id", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("overlay_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enrichment_job_id"],
            ["exam_answer_key_enrichment_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "enrichment_job_id",
            name="uq_exam_answer_key_proposed_overlays_enrichment_job_id",
        ),
    )
    op.create_index(
        "ix_exam_answer_key_proposed_overlays_enrichment_job_id",
        "exam_answer_key_proposed_overlays",
        ["enrichment_job_id"],
    )
    op.create_index(
        "ix_exam_answer_key_proposed_overlays_conversion_job_id",
        "exam_answer_key_proposed_overlays",
        ["conversion_job_id"],
    )
    op.create_index(
        "ix_exam_answer_key_proposed_overlays_owner_user_id",
        "exam_answer_key_proposed_overlays",
        ["owner_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_exam_answer_key_proposed_overlays_owner_user_id",
        table_name="exam_answer_key_proposed_overlays",
    )
    op.drop_index(
        "ix_exam_answer_key_proposed_overlays_conversion_job_id",
        table_name="exam_answer_key_proposed_overlays",
    )
    op.drop_index(
        "ix_exam_answer_key_proposed_overlays_enrichment_job_id",
        table_name="exam_answer_key_proposed_overlays",
    )
    op.drop_table("exam_answer_key_proposed_overlays")

    op.drop_index(
        "ix_exam_answer_key_enrichment_jobs_claim",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_index(
        "ix_exam_answer_key_enrichment_jobs_status",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_index(
        "ix_exam_answer_key_enrichment_jobs_owner_user_id",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_index(
        "ix_exam_answer_key_enrichment_jobs_conversion_job_id",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_table("exam_answer_key_enrichment_jobs")

    op.drop_index(
        "ix_exam_answer_key_token_leases_job_id",
        table_name="exam_answer_key_token_leases",
    )
    op.drop_index(
        "ix_exam_answer_key_token_leases_day",
        table_name="exam_answer_key_token_leases",
    )
    op.drop_table("exam_answer_key_token_leases")
