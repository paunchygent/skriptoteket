from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ToolSessionTurnStatus = Literal["pending", "complete", "failed", "cancelled"]


class ToolSessionTurn(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_session_id: UUID
    status: ToolSessionTurnStatus
    failure_outcome: str | None
    provider: str | None
    correlation_id: UUID | None
    sequence: int
    created_at: datetime
    updated_at: datetime
