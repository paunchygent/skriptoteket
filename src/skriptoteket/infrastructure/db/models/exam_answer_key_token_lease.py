"""ORM model for the answer-key daily token lease table.

Purpose:
    Persist non-refundable per-attempt token leases partitioned by UTC day,
    the single Postgres accounting surface for remote answer-key calls
    (ST-SKRIPT-39-02 term S1).

Relationships:
    Mapped by ``infrastructure.repositories.exam_answer_key_token_leases``;
    domain rules live in
    ``domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease``.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ExamAnswerKeyTokenLeaseModel(Base):
    __tablename__ = "exam_answer_key_token_leases"
    __table_args__ = (Index("ix_exam_answer_key_token_leases_day", "utc_day"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    utc_day: Mapped[date] = mapped_column(Date, nullable=False)
    job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_profile_id: Mapped[str] = mapped_column(String(128), nullable=False)

    reserved_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False)

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
