"""Classroom Planner PlanDraft SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from skriptoteket.infrastructure.db.base import Base


class PlanDraftModel(Base):
    """An active draft of a seating/grouping plan in the Classroom Planner."""

    __tablename__ = "classroom_planner_plan_drafts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    roster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_rosters.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_room_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_mode_id: Mapped[str] = mapped_column(String(255), nullable=False)

    revision: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    group_count: Mapped[int] = mapped_column(default=6, server_default="6", nullable=False)

    # Relationships
    group_assignments: Mapped[list[GroupAssignmentModel]] = relationship(
        "GroupAssignmentModel",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    seat_assignments: Mapped[list[SeatAssignmentModel]] = relationship(
        "SeatAssignmentModel",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

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


class GroupAssignmentModel(Base):
    """SQLAlchemy model for a group assignment within a draft."""

    __tablename__ = "classroom_planner_group_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship
    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="group_assignments"
    )


class SeatAssignmentModel(Base):
    """SQLAlchemy model for a seat assignment within a draft."""

    __tablename__ = "classroom_planner_seat_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    seat_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationship
    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="seat_assignments"
    )
