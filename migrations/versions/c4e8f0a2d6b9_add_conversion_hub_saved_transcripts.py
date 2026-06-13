"""Add durable Conversion Hub saved transcripts.

Domain purpose:
  Store owner-scoped canonical transcript JSON and provenance so transcript
  readback survives Sir Convert artifact retention while formatter outputs stay
  outside this persistence boundary.

Relationships:
  - References `users.id` and `conversion_hub_jobs.id`.
  - Backed by `ConversionHubSavedTranscriptModel`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4e8f0a2d6b9"
down_revision: str | None = "b3e7a1c9d4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "conversion_hub_jobs",
        "output_format",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_table(
        "conversion_hub_saved_transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_hub_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sir_convert_job_id", sa.String(length=255), nullable=False),
        sa.Column("artifact_key", sa.String(length=128), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=False),
        sa.Column("transcript_schema_version", sa.String(length=64), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("diarization_mode", sa.String(length=64), nullable=False),
        sa.Column("speaker_count", sa.Integer(), nullable=True),
        sa.Column("speaker_min", sa.Integer(), nullable=True),
        sa.Column("speaker_max", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("transcript_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["conversion_hub_job_id"],
            ["conversion_hub_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            "sir_convert_job_id",
            name="uq_conversion_hub_saved_transcripts_owner_upstream",
        ),
    )
    op.create_index(
        op.f("ix_conversion_hub_saved_transcripts_owner_user_id"),
        "conversion_hub_saved_transcripts",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conversion_hub_saved_transcripts_owner_created",
        "conversion_hub_saved_transcripts",
        ["owner_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_conversion_hub_saved_transcripts_job_id",
        "conversion_hub_saved_transcripts",
        ["conversion_hub_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversion_hub_saved_transcripts_job_id",
        table_name="conversion_hub_saved_transcripts",
    )
    op.drop_index(
        "ix_conversion_hub_saved_transcripts_owner_created",
        table_name="conversion_hub_saved_transcripts",
    )
    op.drop_index(
        op.f("ix_conversion_hub_saved_transcripts_owner_user_id"),
        table_name="conversion_hub_saved_transcripts",
    )
    op.drop_table("conversion_hub_saved_transcripts")
    op.alter_column(
        "conversion_hub_jobs",
        "output_format",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
