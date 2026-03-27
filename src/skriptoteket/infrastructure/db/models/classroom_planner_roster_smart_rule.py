"""SQLAlchemy models for roster-owned classroom planner smart rules.

This module persists the class-global smart-rule set that belongs to one
roster. These tables intentionally live outside the plan-draft aggregate so
multiple drafts for the same class can share one stable rule set with its own
optimistic-concurrency revision.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class RosterSmartRuleSetModel(Base):
    """Persist the revision-bearing smart-rule aggregate root for one roster."""

    __tablename__ = "classroom_planner_roster_smart_rule_sets"

    roster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_rosters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RosterSeatingPreferenceModel(Base):
    """Persist one roster-owned seating preference for a student."""

    __tablename__ = "classroom_planner_roster_seating_preferences"
    __table_args__ = (
        UniqueConstraint("roster_id", "student_id", name="uq_cp_roster_seating_pref"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    roster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_roster_smart_rule_sets.roster_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    student_id: Mapped[str] = mapped_column(String(255), nullable=False)
    near_teacher: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class RosterRelationshipRuleModel(Base):
    """Persist one roster-owned relationship rule."""

    __tablename__ = "classroom_planner_roster_relationship_rules"
    __table_args__ = (
        UniqueConstraint("roster_id", "rule_id", name="uq_cp_roster_relationship_rule"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    roster_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_roster_smart_rule_sets.roster_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    student_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
