"""SQLAlchemy models for Klassrumskartan share artifacts.

Purpose:
    Persist immutable classroom-planner share artifacts separately from export
    jobs, mutable drafts, Vault files, and public guest workspace state.

Relationships:
    - Used by `infrastructure.repositories.classroom_planner_share_artifacts`.
    - References users and planner drafts only when an authenticated owned share
      has those server-side records.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.application.curated_apps.classroom_planner.shares import JsonObject
from skriptoteket.infrastructure.db.base import Base


class ClassroomPlannerShareArtifactModel(Base):
    """Persist one immutable public share artifact."""

    __tablename__ = "classroom_planner_share_artifacts"
    __table_args__ = (
        Index(
            "ix_cp_share_artifacts_owner_draft_kind_created",
            "owner_user_id",
            "draft_id",
            "draft_kind",
            "created_at",
        ),
        Index("ix_cp_share_artifacts_expires_at", "expires_at"),
        Index("ix_cp_share_artifacts_revoked_at", "revoked_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    draft_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    draft_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("classroom_planner_plan_drafts.id"),
        nullable=True,
        index=True,
    )
    roster_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    template_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    source_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    public_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    preview_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    renderer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    presentation_schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    presentation_hash: Mapped[str] = mapped_column(String(96), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(96), nullable=False)
    presentation_payload: Mapped[JsonObject | None] = mapped_column(JSONB, nullable=True)
    rendered_html: Mapped[str] = mapped_column(Text, nullable=False)
    rendered_css: Mapped[str] = mapped_column(Text, nullable=False)
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
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
