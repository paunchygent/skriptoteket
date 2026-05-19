"""SQLAlchemy models for Exam Converter correction sessions.

Purpose:
  Persist Skriptoteket-owned correction-session truth for authenticated Exam
  Converter jobs while preserving exact producer source bindings per intent.

Relationships:
  - Session rows are owner/job scoped to `conversion_hub_jobs`.
  - Active intent rows are loaded by the correction-session repository.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ExamConverterCorrectionSessionModel(Base):
    """Persist one owner-scoped correction session for a Conversion Hub job."""

    __tablename__ = "exam_converter_correction_sessions"
    __table_args__ = (
        Index(
            "uq_exam_conv_corr_sessions_owner_job",
            "owner_user_id",
            "conversion_hub_job_id",
            unique=True,
        ),
        Index("ix_exam_conv_corr_sessions_owner_updated", "owner_user_id", "updated_at"),
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
        index=True,
    )
    source_authoring_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    source_bundle_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_state_sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    source_state_signature: Mapped[str] = mapped_column(Text, nullable=False)
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
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


class ExamConverterCorrectionIntentModel(Base):
    """Persist one correction intent row under a correction session."""

    __tablename__ = "exam_converter_correction_intents"
    __table_args__ = (
        Index(
            "uq_exam_conv_corr_intents_active_target",
            "session_id",
            "target_key",
            unique=True,
            postgresql_where=text("is_active IS TRUE"),
        ),
        Index(
            "uq_exam_conv_corr_intents_active_family",
            "session_id",
            "conflict_family",
            unique=True,
            postgresql_where=text("is_active IS TRUE AND conflict_family IS NOT NULL"),
        ),
        Index("ix_exam_conv_corr_intents_session_active", "session_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("exam_converter_correction_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correction_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_key: Mapped[str] = mapped_column(Text, nullable=False)
    conflict_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_item_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    source_binding: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    target: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
