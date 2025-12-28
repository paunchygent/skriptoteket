from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AcquireDraftLockCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    draft_head_id: UUID
    force: bool = False


class AcquireDraftLockResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
    draft_head_id: UUID
    locked_by_user_id: UUID
    expires_at: datetime
    is_owner: bool


class ReleaseDraftLockCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID


class ReleaseDraftLockResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: UUID
