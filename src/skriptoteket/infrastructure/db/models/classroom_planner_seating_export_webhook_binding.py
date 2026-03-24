"""SQLAlchemy model for the shared seating-export webhook binding.

Purpose:
    Persist one canonical Sir Convert webhook subscription record for
    classroom-planner seating exports so concurrent export starts can coordinate
    through a row lock instead of racing on the latest job row.

Relationships:
    - Used by `infrastructure.repositories.classroom_planner_export_webhook_bindings`.
    - Read and updated by seating export-job handlers during shared subscription
      creation and reuse.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class SeatingExportWebhookBindingModel(Base):
    """Persist the single shared webhook binding for seating exports."""

    __tablename__ = "classroom_planner_seating_export_webhook_bindings"

    binding_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    callback_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
