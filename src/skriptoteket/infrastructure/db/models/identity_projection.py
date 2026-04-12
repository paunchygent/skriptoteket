"""SQLAlchemy models for realm-aware identity projections.

Purpose:
    Store explicit product realm subject mappings and their audit events for
    HuleEdu-derived Skriptoteket app continuation.

Relationships:
    - Maps `skriptoteket.domain.identity.projections` domain models.
    - References `users` without storing provider subjects on the user row.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class IdentityProjectionModel(Base):
    __tablename__ = "identity_projections"
    __table_args__ = (
        UniqueConstraint(
            "product_identity_realm",
            "realm_subject_id",
            name="uq_identity_projections_realm_subject",
        ),
        Index("ix_identity_projections_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_identity_realm: Mapped[str] = mapped_column(String(64), nullable=False)
    realm_subject_id: Mapped[str] = mapped_column(String(255), nullable=False)
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


class IdentityProjectionEventModel(Base):
    __tablename__ = "identity_projection_events"
    __table_args__ = (
        Index("ix_identity_projection_events_user_id", "user_id"),
        Index("ix_identity_projection_events_projection_id", "projection_id"),
        Index("ix_identity_projection_events_created_at", "created_at"),
        Index("ix_identity_projection_events_type", "event_type"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    projection_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("identity_projections.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_identity_realm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    realm_subject_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    context_jti: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
