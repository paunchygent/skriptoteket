"""SQLAlchemy model for durable Conversion Hub transcript JSON.

Domain purpose:
  Persist owner-scoped transcript JSON and provenance after Sir Convert artifact
  retention expires, while keeping future formatter/export projections separate
  from the canonical saved transcript.

Relationships:
  - Linked to `users.id` and `conversion_hub_jobs.id` for authorization and
    provenance.
  - Mapped by `infrastructure.repositories.conversion_hub_saved_transcripts`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ConversionHubSavedTranscriptModel(Base):
    """Persist one canonical transcript JSON save."""

    __tablename__ = "conversion_hub_saved_transcripts"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "sir_convert_job_id",
            name="uq_conversion_hub_saved_transcripts_owner_upstream",
        ),
        Index(
            "ix_conversion_hub_saved_transcripts_owner_created",
            "owner_user_id",
            "created_at",
        ),
        Index(
            "ix_conversion_hub_saved_transcripts_job_id",
            "conversion_hub_job_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversion_hub_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversion_hub_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    sir_convert_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    transcript_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    diarization_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    speaker_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaker_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speaker_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    transcript_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
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
