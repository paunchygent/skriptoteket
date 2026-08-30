"""ORM model for durable anonymous Exam Converter jobs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import DateTime, Index, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class PublicExamConverterJobModel(Base):
    """Persist public inputs and lifecycle while artifacts remain file-backed."""

    __tablename__ = "public_exam_converter_jobs"
    __table_args__ = (Index("ix_public_exam_converter_jobs_claim", "status", "submitted_at"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    requested_targets: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_dxe: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    graded_result_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graded_result_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graded_result_pdf: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, JsonValue] | None] = mapped_column(JSONB, nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
