from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class LoginEventModel(Base):
    __tablename__ = "login_events"
    __table_args__ = (
        Index("ix_login_events_user_id", "user_id"),
        Index("ix_login_events_created_at", "created_at"),
        Index("ix_login_events_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text(), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    geo_country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    geo_region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geo_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    geo_latitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    geo_longitude: Mapped[float | None] = mapped_column(Float(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
