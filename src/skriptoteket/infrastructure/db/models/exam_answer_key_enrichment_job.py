"""ORM model for machine answer-key enrichment jobs.

Purpose:
    Persist the durable execution-worker jobs that produce machine-proposed
    answer keys for in-process Exam Converter conversions.

Relationships:
    Mapped by ``infrastructure.repositories.exam_answer_key_enrichment_jobs``;
    the application contract lives in
    ``application.curated_apps.exam_answer_key_enrichment``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ExamAnswerKeyEnrichmentJobModel(Base):
    __tablename__ = "exam_answer_key_enrichment_jobs"
    __table_args__ = (Index("ix_exam_answer_key_enrichment_jobs_claim", "status", "available_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    conversion_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversion_hub_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    input_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_dxe: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
