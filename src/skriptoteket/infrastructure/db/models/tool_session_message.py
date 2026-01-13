from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ToolSessionMessageModel(Base):
    __tablename__ = "tool_session_messages"
    __table_args__ = (
        Index("ix_tool_session_messages_session_sequence", "tool_session_id", "sequence"),
        Index("ix_tool_session_messages_session_message_id", "tool_session_id", "message_id"),
        Index("ix_tool_session_messages_session_turn_id", "tool_session_id", "turn_id"),
        UniqueConstraint(
            "tool_session_id",
            "message_id",
            name="uq_tool_session_messages_session_message_id",
        ),
        UniqueConstraint(
            "tool_session_id",
            "turn_id",
            "role",
            name="uq_tool_session_messages_turn_role",
        ),
        ForeignKeyConstraint(
            ["tool_session_id", "turn_id"],
            ["tool_session_turns.tool_session_id", "tool_session_turns.id"],
            ondelete="CASCADE",
            name="fk_tool_session_messages_turn",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tool_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tool_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    message_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    meta: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
