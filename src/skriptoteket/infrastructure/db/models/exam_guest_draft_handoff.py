"""ORM model for the exam guest draft handoff ledger.

Purpose:
    Persist one handoff fact per ``(owner_user_id, draft_id)`` so the signed-in
    guest-draft import creates the exam in Mina filer exactly once
    (TASK-SKRIPT-41-02-02 P5).

Relationships:
    Mapped by ``infrastructure.repositories.exam_guest_draft_handoffs``; the
    claim semantics live in ``protocols.exam_workspace_guest_drafts``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ExamGuestDraftHandoffModel(Base):
    """Persist one guest-draft handoff fact for one owner/draft pair."""

    __tablename__ = "exam_guest_draft_handoffs"

    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    draft_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    lineage_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
