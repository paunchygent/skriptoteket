"""ORM model for the public request-window counter table.

Purpose:
    Persist one hourly counter row per ``(bucket, caller_key, window_start)`` so
    the public guest limiter is shared by workers and survives restarts.

Relationships:
    Mapped by ``infrastructure.repositories.public_request_windows``; the
    bucket and caller vocabulary lives in ``protocols.public_request_limits``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class PublicRequestWindowModel(Base):
    __tablename__ = "public_request_windows"
    __table_args__ = (Index("ix_public_request_windows_window_start", "window_start"),)

    bucket: Mapped[str] = mapped_column(String(32), primary_key=True)
    caller_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False)
