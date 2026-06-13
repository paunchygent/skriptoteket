"""SQLAlchemy model for locally owned Conversion Hub jobs.

Purpose:
  Persist Conversion Hub jobs inside Skriptoteket so the product, not the
  upstream conversion engine, owns job identity, authorization, and status
  refresh behavior.

Relationships:
  - Used by `infrastructure.repositories.conversion_hub_jobs`.
  - Linked to `users.id` for owner-scoped access control.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ConversionHubJobModel(Base):
    """Persist one locally owned Conversion Hub job."""

    __tablename__ = "conversion_hub_jobs"
    __table_args__ = (
        Index("ix_conversion_hub_jobs_owner_created", "owner_user_id", "created_at"),
        Index(
            "uq_conversion_hub_jobs_upstream",
            "upstream_job_id",
            unique=True,
            postgresql_where=text("upstream_job_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_format: Mapped[str] = mapped_column(String(16), nullable=False)
    output_format: Mapped[str] = mapped_column(String(32), nullable=False)
    pdf_paper_size: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pdf_orientation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pdf_margins_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upstream_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
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
