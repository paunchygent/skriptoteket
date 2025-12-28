from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DraftLock(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    tool_id: UUID
    draft_head_id: UUID
    locked_by_user_id: UUID
    locked_at: datetime
    expires_at: datetime
    forced_by_user_id: UUID | None = None
