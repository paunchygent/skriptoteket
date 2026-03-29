"""SQLAlchemy model for registration allowlist domains.

Purpose:
  Persist normalized school-sector root domains that may later be used for
  registration allow/deny checks.

Relationships:
  - Mirrors `skriptoteket.domain.identity.models.AllowedDomain`.
  - Used by `PostgreSQLAllowedDomainRepository` and Alembic metadata discovery.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class AllowedDomainModel(Base):
    __tablename__ = "allowed_domains"

    domain: Mapped[str] = mapped_column(String(255), primary_key=True)
    org_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
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
