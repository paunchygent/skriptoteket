from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ToolRunModel(Base):
    __tablename__ = "tool_runs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    tool_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tool_versions.id"),
        index=True,
        nullable=True,
    )

    source_kind: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        server_default="tool_version",
    )
    curated_app_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    curated_app_version: Mapped[str | None] = mapped_column(String(128), nullable=True)

    context: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    requested_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workdir_path: Mapped[str] = mapped_column(Text, nullable=False)
    input_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    input_manifest: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{\"files\":[]}'::jsonb"),
    )
    input_values: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    html_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts_manifest: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ui_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
