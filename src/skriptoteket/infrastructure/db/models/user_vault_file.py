from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class UserVaultFileModel(Base):
    """One Mina filer row: a stored file, an exam document or a saved exam export.

    Exam documents keep their lineage in exactly one active row; a saved export
    shares its exam's lineage and is told apart by `export_format`.
    """

    __tablename__ = "user_vault_files"
    __table_args__ = (
        Index(
            "uq_user_vault_files_document_exam",
            "user_id",
            "document_lineage_id",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND export_format IS NULL AND document_lineage_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_user_vault_files_document_export",
            "user_id",
            "document_lineage_id",
            "export_format",
            unique=True,
            postgresql_where=text("export_format IS NOT NULL AND document_lineage_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_run_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tool_runs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    source_artifact_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_lineage_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    document_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    export_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    document_saved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    trashed_with_exam: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class ExamWorkspaceHistoryModel(Base):
    """The cursor and position of an exam's undo history; steps and pictures live in own rows."""

    __tablename__ = "exam_workspace_history"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lineage_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    cursor: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    current_step_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    baseline_step_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    lease_holder_tab_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    lease_renewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    lease_takeover_requested_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )


class ExamWorkspaceHistoryStepModel(Base):
    """One stored undo step: its document without picture bytes, compressed.

    Pictures are stored once per exam in ``exam_workspace_history_assets`` and
    referenced by asset id from the document; ``asset_ids`` projects that list
    so picture garbage collection never parses step documents.
    """

    __tablename__ = "exam_workspace_history_steps"
    __table_args__ = (
        Index(
            "ix_exam_workspace_history_steps_order",
            "user_id",
            "lineage_id",
            "position",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lineage_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    step_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    document: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    asset_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    notes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)


class ExamWorkspaceHistoryAssetModel(Base):
    """One picture stored once per exam, referenced by asset id from step documents."""

    __tablename__ = "exam_workspace_history_assets"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    lineage_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
