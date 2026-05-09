"""SQLAlchemy models for classroom planner drafts.

This module persists the mutable classroom-planner workspace used by the
active fundamentals flow. Draft child tables capture group structure and
seating assignments scoped to one plan draft, while roster-global smart rules
live in separate roster-owned tables.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
        Index(
            "uq_cp_guest_import_identity",
            "owner_user_id",
            "guest_import_identity",
            unique=True,
            postgresql_where=text("guest_import_identity IS NOT NULL"),
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
    task_entry_classroom_selection_mode: Mapped[str] = mapped_column(
        String(32),
        server_default="optional",
        nullable=False,
    )
    smart_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    use_history: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    grouping_seating_distance_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        server_default="active",
        nullable=False,
        index=True,
    )
    guest_import_identity: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    last_opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    history_stack: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    undo_index: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False, default=0)

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
    name_is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

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
