"""ORM model for machine-proposed answer-key overlays.

Purpose:
    Persist the machine-proposed ingestion overlay produced by one enrichment
    job so proposals remain durable, source-bound records under the existing
    overlay semantics (ST-SKRIPT-39-02 term S4).

Relationships:
    Mapped by ``infrastructure.repositories.exam_answer_key_proposed_overlays``;
    the application contract lives in
    ``application.curated_apps.exam_answer_key_enrichment``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ExamAnswerKeyProposedOverlayModel(Base):
    __tablename__ = "exam_answer_key_proposed_overlays"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    enrichment_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_answer_key_enrichment_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    conversion_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), index=True, nullable=False
    )
    owner_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)

    source_file_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    source_ir_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    overlay_json: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
