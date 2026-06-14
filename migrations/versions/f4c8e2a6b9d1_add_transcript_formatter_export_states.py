"""Add transcript formatter export states.

Domain purpose:
  Persist requested formatter artifacts for product-owned transcript export
  states that do not have verified artifact rows yet.

Relationships:
  - References `users.id`, `conversion_hub_saved_transcripts.id`, and
    `conversion_hub_jobs.id`.
  - Backed by `ConversionHubTranscriptFormatterExportStateModel`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4c8e2a6b9d1"
down_revision: str | None = "e9a4b6c8d2f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversion_hub_transcript_formatter_export_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("saved_transcript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversion_hub_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "requested_artifacts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
            "conversion_hub_job_id",
            name="uq_conv_hub_transcript_formatter_export_states_job",
        ),
    )
    op.create_index(
        "ix_conv_hub_formatter_export_states_owner_transcript",
        "conversion_hub_transcript_formatter_export_states",
        ["owner_user_id", "saved_transcript_id"],
        unique=False,
    )
    op.create_index(
        "ix_conv_hub_formatter_export_states_owner_job",
        "conversion_hub_transcript_formatter_export_states",
        ["owner_user_id", "conversion_hub_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conv_hub_formatter_export_states_owner_job",
        table_name="conversion_hub_transcript_formatter_export_states",
    )
    op.drop_index(
        "ix_conv_hub_formatter_export_states_owner_transcript",
        table_name="conversion_hub_transcript_formatter_export_states",
    )
    op.drop_table("conversion_hub_transcript_formatter_export_states")
