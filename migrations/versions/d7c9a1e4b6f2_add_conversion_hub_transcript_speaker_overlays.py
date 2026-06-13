"""Add Conversion Hub transcript speaker overlays.

Domain purpose:
  Store owner-scoped display-name overlays for saved transcript speaker labels
  while preserving canonical transcript JSON as immutable product truth.

Relationships:
  - References `users.id` and `conversion_hub_saved_transcripts.id`.
  - Backed by `ConversionHubTranscriptSpeakerOverlayModel`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7c9a1e4b6f2"
down_revision: str | None = "c4e8f0a2d6b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversion_hub_transcript_speaker_overlays",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("saved_transcript_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_speaker_label", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
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
            ["owner_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["saved_transcript_id"],
            ["conversion_hub_saved_transcripts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "canonical_speaker_label",
            name="uq_conv_hub_transcript_speaker_overlays_label",
        ),
        sa.UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "display_name",
            name="uq_conv_hub_transcript_speaker_overlays_display",
        ),
    )
    op.create_index(
        op.f("ix_conversion_hub_transcript_speaker_overlays_owner_user_id"),
        "conversion_hub_transcript_speaker_overlays",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_conv_hub_transcript_speaker_overlays_owner_transcript",
        "conversion_hub_transcript_speaker_overlays",
        ["owner_user_id", "saved_transcript_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conv_hub_transcript_speaker_overlays_owner_transcript",
        table_name="conversion_hub_transcript_speaker_overlays",
    )
    op.drop_index(
        op.f("ix_conversion_hub_transcript_speaker_overlays_owner_user_id"),
        table_name="conversion_hub_transcript_speaker_overlays",
    )
    op.drop_table("conversion_hub_transcript_speaker_overlays")
