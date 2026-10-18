"""Retire the old signed-in exam converter's tables and the dxe enrichment lane.

Revision ID: e8a3c5f1b7d2
Revises: d71e4a6c9b20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e8a3c5f1b7d2"
down_revision: str | Sequence[str] | None = "d71e4a6c9b20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop correction and overlay tables, dxe jobs, the conversion-job link and submission keys."""

    op.drop_table("exam_converter_correction_intents")
    op.drop_table("exam_converter_correction_sessions")
    op.drop_table("exam_answer_key_proposed_overlays")

    op.execute("DELETE FROM exam_answer_key_enrichment_jobs WHERE source_kind = 'dxe'")

    op.drop_constraint(
        "exam_answer_key_enrichment_jobs_conversion_job_id_fkey",
        "exam_answer_key_enrichment_jobs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_exam_answer_key_enrichment_jobs_conversion_job_id",
        "exam_answer_key_enrichment_jobs",
        type_="unique",
    )
    op.drop_index(
        "ix_exam_answer_key_enrichment_jobs_conversion_job_id",
        table_name="exam_answer_key_enrichment_jobs",
    )
    op.drop_column("exam_answer_key_enrichment_jobs", "conversion_job_id")

    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "source_kind",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default=None,
    )

    op.drop_index(
        "uq_conversion_hub_jobs_owner_submission_key",
        table_name="conversion_hub_jobs",
    )
    op.drop_column("conversion_hub_jobs", "submission_idempotency_key")


def downgrade() -> None:
    """Recreate the dropped schema; deleted rows are not restored."""

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

    op.alter_column(
        "exam_answer_key_enrichment_jobs",
        "source_kind",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default="dxe",
    )

    op.add_column(
        "exam_answer_key_enrichment_jobs",
        sa.Column("conversion_job_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "exam_answer_key_enrichment_jobs_conversion_job_id_fkey",
        "exam_answer_key_enrichment_jobs",
        "conversion_hub_jobs",
        ["conversion_job_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_exam_answer_key_enrichment_jobs_conversion_job_id",
        "exam_answer_key_enrichment_jobs",
        ["conversion_job_id"],
    )
    op.create_index(
        "ix_exam_answer_key_enrichment_jobs_conversion_job_id",
        "exam_answer_key_enrichment_jobs",
        ["conversion_job_id"],
    )

    op.create_table(
        "exam_answer_key_proposed_overlays",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("enrichment_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_job_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("workspace_lineage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_document_revision", sa.Integer(), nullable=True),
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

    op.create_table(
        "exam_converter_correction_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_hub_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_authoring_schema_version", sa.String(length=64), nullable=False),
        sa.Column("source_bundle_id", sa.String(length=255), nullable=True),
        sa.Column("source_file_sha256", sa.String(length=128), nullable=True),
        sa.Column("source_state_sha256", sa.String(length=128), nullable=False),
        sa.Column("source_state_signature", sa.Text(), nullable=False),
        sa.Column("session_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("session_version >= 0", name="ck_exam_conv_corr_session_version"),
        sa.ForeignKeyConstraint(
            ["conversion_hub_job_id"], ["conversion_hub_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_converter_correction_sessions_owner_user_id",
        "exam_converter_correction_sessions",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_converter_correction_sessions_job_id",
        "exam_converter_correction_sessions",
        ["conversion_hub_job_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_conv_corr_sessions_owner_updated",
        "exam_converter_correction_sessions",
        ["owner_user_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "uq_exam_conv_corr_sessions_owner_job",
        "exam_converter_correction_sessions",
        ["owner_user_id", "conversion_hub_job_id"],
        unique=True,
    )

    op.create_table(
        "exam_converter_correction_intents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entry_id", sa.String(length=255), nullable=False),
        sa.Column("correction_kind", sa.String(length=64), nullable=False),
        sa.Column("target_key", sa.Text(), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(length=64), nullable=False),
        sa.Column("source_item_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("source_binding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_exam_conv_corr_intent_sequence"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["exam_converter_correction_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_exam_converter_correction_intents_session_id",
        "exam_converter_correction_intents",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_exam_conv_corr_intents_session_active",
        "exam_converter_correction_intents",
        ["session_id", "is_active"],
        unique=False,
    )
    op.create_index(
        "uq_exam_conv_corr_intents_active_target",
        "exam_converter_correction_intents",
        ["session_id", "target_key"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )
