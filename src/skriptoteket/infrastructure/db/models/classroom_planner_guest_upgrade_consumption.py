"""SQLAlchemy models for classroom-planner guest-upgrade consumption.

This module persists the one-time authenticated guest-upgrade consumption
ledger for Klassrumskartan. It keeps import-bridge truth separate from both
browser-owned guest authoring eligibility and planner artifact inference.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ClassroomPlannerGuestUpgradeConsumptionModel(Base):
    """Persist one guest-upgrade consumption fact for one owner/app pair."""

    __tablename__ = "classroom_planner_guest_upgrade_consumptions"
    __table_args__ = (
        Index(
            "uq_cp_guest_upgrade_consumptions_owner_app",
            "owner_user_id",
            "app_id",
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    app_id: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(String(255), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
