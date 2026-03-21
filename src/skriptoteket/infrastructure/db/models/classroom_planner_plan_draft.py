"""SQLAlchemy models for classroom planner drafts and snapshots.

This module persists the mutable classroom planner workspace and immutable
snapshot history. Draft child tables keep group structure, assignments,
teacher-only metadata, pair constraints, and planning profile data scoped to a
single plan draft.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from skriptoteket.infrastructure.db.base import Base


class PlanDraftModel(Base):
    """Persist the mutable root draft record."""

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
    engine_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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
    pair_constraints: Mapped[list[PairConstraintModel]] = relationship(
        "PairConstraintModel",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    planning_profile: Mapped[PlanningProfileModel | None] = relationship(
        "PlanningProfileModel",
        back_populates="draft",
        cascade="all, delete-orphan",
        lazy="selectin",
        uselist=False,
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
    independent_focus_support: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stability_preference: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    preferred_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avoid_zone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="student_planning_meta"
    )


class PairConstraintModel(Base):
    """Persist a pairwise draft-scoped planning constraint."""

    __tablename__ = "classroom_planner_pair_constraints"
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            "student_id_a",
            "student_id_b",
            "kind",
            name="uq_cp_pair_constraint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id_a: Mapped[str] = mapped_column(String(255), nullable=False)
    student_id_b: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(255), nullable=False)
    strength: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="pair_constraints"
    )


class PlanningProfileModel(Base):
    """Persist a draft-scoped planning profile and explicit weights."""

    __tablename__ = "classroom_planner_planning_profiles"
    __table_args__ = (UniqueConstraint("draft_id", name="uq_cp_planning_profile_draft"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    profile_kind: Mapped[str] = mapped_column(String(255), nullable=False)
    enable_student_meta: Mapped[bool] = mapped_column(nullable=False, default=True)
    enable_pair_constraints: Mapped[bool] = mapped_column(nullable=False, default=True)
    enable_zone_preferences: Mapped[bool] = mapped_column(nullable=False, default=True)
    enable_history_rules: Mapped[bool] = mapped_column(nullable=False, default=False)
    teacher_proximity_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    focus_support_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stability_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    balance_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rotation_weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    draft: Mapped[PlanDraftModel] = relationship(
        "PlanDraftModel", back_populates="planning_profile"
    )


class ArrangementSnapshotModel(Base):
    """Persist an immutable finalized arrangement snapshot."""

    __tablename__ = "classroom_planner_arrangement_snapshots"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_draft_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    lesson_mode_id: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
