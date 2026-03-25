"""SQLAlchemy models for classroom-planner seating export jobs.

Purpose:
    Persist explicit seating export jobs separately from mutable draft state so
    async conversion lifecycle, webhook bookkeeping, and Vault delivery can be
    tracked without overloading planner drafts or generic tool runs.

Relationships:
    - Used by `infrastructure.repositories.classroom_planner_export_jobs`.
    - Linked to plan drafts, users, and optional Vault files.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class SeatingExportJobModel(Base):
    """Persist one explicit seating export job."""

    __tablename__ = "classroom_planner_seating_export_jobs"
    __table_args__ = (
        Index(
            "ix_cp_seating_export_jobs_owner_created",
            "owner_user_id",
            "created_at",
        ),
        Index(
            "uq_cp_seating_export_jobs_upstream",
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
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    roster_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    template_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    export_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    layout_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paper_size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    output_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    upstream_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vault_file_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_vault_files.id", ondelete="SET NULL"),
        nullable=True,
    )
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
