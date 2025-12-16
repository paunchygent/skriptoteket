from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from skriptoteket.infrastructure.db.base import Base


class ToolMaintainerModel(Base):
    __tablename__ = "tool_maintainers"

    tool_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
        nullable=False,
    )
