"""SQLAlchemy models for classroom planner drafts.

This module persists the mutable classroom-planner workspace used by the
active fundamentals flow. Draft child tables capture group structure, seating
assignments, and teacher-only student notes scoped to one plan draft.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from skriptoteket.infrastructure.db.base import Base


class PlanDraftModel(Base):
    """Persist the mutable root draft record."""

    __tablename__ = "classroom_planner_plan_drafts"
    __table_args__ = (
        Index(
            "uq_cp_active_draft_roster_kind",
            "owner_user_id",
            "roster_id",
            "draft_kind",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        CheckConstraint(
            "(draft_kind = 'grouping') OR (template_id IS NOT NULL)",
            name="ck_cp_seating_draft_requires_template",
        ),
    )

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
    draft_kind: Mapped[str] = mapped_column(
        String(32),
        server_default="seating",
        nullable=False,
        index=True,
    )
    template_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_room_templates.id", ondelete="CASCADE"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        server_default="active",
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    last_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    groups: Mapped[list[DraftGroupModel]] = relationship(
        "DraftGroupModel",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DraftGroupModel.sort_order",
    )
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
    student_planning_meta: Mapped[list[StudentPlanningMetaModel]] = relationship(
        "StudentPlanningMetaModel",
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


class DraftGroupModel(Base):
    """Persist a teacher-managed draft group bucket."""

    __tablename__ = "classroom_planner_draft_groups"
    __table_args__ = (UniqueConstraint("draft_id", "group_id", name="uq_cp_draft_group_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    group_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    draft: Mapped[PlanDraftModel] = relationship("PlanDraftModel", back_populates="groups")


class GroupAssignmentModel(Base):
    """Persist one student-to-group assignment within a draft."""

    __tablename__ = "classroom_planner_group_assignments"
    __table_args__ = (UniqueConstraint("draft_id", "student_id", name="uq_cp_group_assignment"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[str] = mapped_column(String(255), nullable=False)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="group_assignments"
    )


class SeatAssignmentModel(Base):
    """Persist one student-to-seat assignment within a draft."""

    __tablename__ = "classroom_planner_seat_assignments"
    __table_args__ = (
        UniqueConstraint("draft_id", "student_id", name="uq_cp_seat_assignment_student"),
        UniqueConstraint("draft_id", "seat_id", name="uq_cp_seat_assignment_seat"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    seat_id: Mapped[str] = mapped_column(String(255), nullable=False)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="seat_assignments"
    )


class StudentPlanningMetaModel(Base):
    """Persist teacher-only student planning metadata for a draft."""

    __tablename__ = "classroom_planner_student_planning_meta"
    __table_args__ = (UniqueConstraint("draft_id", "student_id", name="uq_cp_student_meta"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_proximity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stability_preference: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preferred_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avoid_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="student_planning_meta"
    )
