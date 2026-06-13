"""SQLAlchemy model for Conversion Hub transcript speaker overlays.

Domain purpose:
  Persist owner-scoped speaker display-name overlays for saved transcripts
  without mutating the canonical Sir Convert transcript JSON.

Relationships:
  - Linked to `conversion_hub_saved_transcripts.id` for transcript ownership.
  - Mapped by `infrastructure.repositories.conversion_hub_saved_transcripts`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ConversionHubTranscriptSpeakerOverlayModel(Base):
    """Persist one speaker display-name overlay for a saved transcript."""

    __tablename__ = "conversion_hub_transcript_speaker_overlays"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "canonical_speaker_label",
            name="uq_conv_hub_transcript_speaker_overlays_label",
        ),
        UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "display_name",
            name="uq_conv_hub_transcript_speaker_overlays_display",
        ),
        Index(
            "ix_conv_hub_transcript_speaker_overlays_owner_transcript",
            "owner_user_id",
            "saved_transcript_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    saved_transcript_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversion_hub_saved_transcripts.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_speaker_label: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
