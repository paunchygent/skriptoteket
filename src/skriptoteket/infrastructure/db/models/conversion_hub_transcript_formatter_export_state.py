"""SQLAlchemy model for transcript formatter export state.

Domain purpose:
  Persist owner-scoped formatter export intent that is not represented by
  artifact rows, especially pending, running, and failed product states.

Relationships:
  - References `users.id`, `conversion_hub_saved_transcripts.id`, and
    `conversion_hub_jobs.id`.
  - Mapped by `infrastructure.repositories.conversion_hub_transcript_formatter_export_states`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ConversionHubTranscriptFormatterExportStateModel(Base):
    """Persist product-owned formatter export intent for one local job."""

    __tablename__ = "conversion_hub_transcript_formatter_export_states"
    __table_args__ = (
        UniqueConstraint(
            "conversion_hub_job_id",
            name="uq_conv_hub_transcript_formatter_export_states_job",
        ),
        Index(
            "ix_conv_hub_formatter_export_states_owner_transcript",
            "owner_user_id",
            "saved_transcript_id",
        ),
        Index(
            "ix_conv_hub_formatter_export_states_owner_job",
            "owner_user_id",
            "conversion_hub_job_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    saved_transcript_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversion_hub_saved_transcripts.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversion_hub_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversion_hub_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_artifacts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
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
