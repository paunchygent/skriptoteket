"""SQLAlchemy model for explicitly blocked email domains.

Purpose:
  Persist normalized personal-provider or otherwise disallowed root domains for
  future registration enforcement.

Relationships:
  - Mirrors `skriptoteket.domain.identity.models.BlockedDomain`.
  - Used by `PostgreSQLBlockedDomainRepository` and Alembic metadata discovery.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class BlockedDomainModel(Base):
    __tablename__ = "blocked_domains"

    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        default=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
