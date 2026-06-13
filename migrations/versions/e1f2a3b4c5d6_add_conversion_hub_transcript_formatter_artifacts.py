"""Add Conversion Hub transcript formatter artifacts.

Domain purpose:
  Persist replay-returned formatter artifact references for saved transcripts so
  download and Mina filer actions authorize against product-owned provenance.

Relationships:
  - References `users.id`, `conversion_hub_saved_transcripts.id`, and
    `conversion_hub_jobs.id`.
  - Backed by `ConversionHubTranscriptFormatterArtifactModel`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e1f2a3b4c5d6"
down_revision: str | None = "d7c9a1e4b6f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversion_hub_transcript_formatter_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("saved_transcript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_hub_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sir_convert_job_id", sa.String(length=255), nullable=False),
        sa.Column("requested_artifact", sa.String(length=16), nullable=False),
        sa.Column("artifact_key", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=128), nullable=False),
        sa.Column("retrieval_path", sa.String(length=500), nullable=False),
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
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["saved_transcript_id"],
            ["conversion_hub_saved_transcripts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversion_hub_job_id"],
            ["conversion_hub_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "artifact_key",
            name="uq_conv_hub_transcript_formatter_artifacts_key",
        ),
    )
    op.create_index(
        op.f("ix_conversion_hub_transcript_formatter_artifacts_owner_user_id"),
        "conversion_hub_transcript_formatter_artifacts",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conv_hub_transcript_formatter_artifacts_owner_transcript",
        "conversion_hub_transcript_formatter_artifacts",
        ["owner_user_id", "saved_transcript_id"],
        unique=False,
    )
    op.create_index(
        "ix_conv_hub_transcript_formatter_artifacts_job",
        "conversion_hub_transcript_formatter_artifacts",
        ["conversion_hub_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conv_hub_transcript_formatter_artifacts_job",
        table_name="conversion_hub_transcript_formatter_artifacts",
    )
    op.drop_index(
        "ix_conv_hub_transcript_formatter_artifacts_owner_transcript",
        table_name="conversion_hub_transcript_formatter_artifacts",
    )
    op.drop_index(
        op.f("ix_conversion_hub_transcript_formatter_artifacts_owner_user_id"),
        table_name="conversion_hub_transcript_formatter_artifacts",
    )
    op.drop_table("conversion_hub_transcript_formatter_artifacts")
