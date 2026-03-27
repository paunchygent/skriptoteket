"""SQLAlchemy models for classroom-planner seating export checkpoints.

This module persists the export-backed seating history used by later smart
assignment slices. It keeps checkpoint identity separate from mutable drafts,
export jobs, and roster-owned smart rules while preserving enough normalized
room and seating data for future history consumers.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class SeatingExportCheckpointModel(Base):
    """Persist one seating-history checkpoint created by successful export."""

    __tablename__ = "classroom_planner_seating_export_checkpoints"
    __table_args__ = (
        Index(
            "ix_cp_seating_export_checkpoints_roster_room_created",
            "roster_id",
            "room_context_hash",
            "created_at",
        ),
        Index(
            "uq_cp_seating_export_checkpoints_source_job",
            "source_export_job_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    roster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_rosters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_room_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_export_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_seating_export_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    room_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    assignment_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    room_context: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    seating_snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
