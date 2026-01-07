from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue

ChatMessageRole = Literal["user", "assistant"]


class ToolSessionMessage(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_session_id: UUID
    message_id: UUID
    role: ChatMessageRole
    content: str
    meta: dict[str, JsonValue] | None
    sequence: int
    created_at: datetime
