"""SQLAlchemy model for transcript formatter replay artifacts.

Domain purpose:
  Persist owner-scoped Sir Convert replay artifact references for saved
  transcripts so download and Mina filer actions can authorize against the
  replay result without trusting browser-supplied job keys.

Relationships:
  - References `users.id`, `conversion_hub_saved_transcripts.id`, and
    `conversion_hub_jobs.id`.
  - Mapped by `infrastructure.repositories.conversion_hub_transcript_formatter_artifacts`.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ConversionHubTranscriptFormatterArtifactModel(Base):
    """Persist one replay-returned formatter artifact reference."""

    __tablename__ = "conversion_hub_transcript_formatter_artifacts"
    __table_args__ = (
        UniqueConstraint(
            "owner_user_id",
            "saved_transcript_id",
            "artifact_key",
            name="uq_conv_hub_transcript_formatter_artifacts_key",
        ),
        Index(
            "ix_conv_hub_transcript_formatter_artifacts_owner_transcript",
            "owner_user_id",
            "saved_transcript_id",
        ),
        Index(
            "ix_conv_hub_transcript_formatter_artifacts_job",
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
    sir_convert_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    requested_artifact: Mapped[str] = mapped_column(String(16), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
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
