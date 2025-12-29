from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.scripting.tool_inputs import ToolInputSchema
from skriptoteket.domain.scripting.tool_settings import ToolSettingsSchema


class SandboxSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    tool_id: UUID
    draft_head_id: UUID
    created_by_user_id: UUID
    entrypoint: str
    source_code: str
    settings_schema: ToolSettingsSchema | None = None
    input_schema: ToolInputSchema | None = None
    usage_instructions: str | None = None
    payload_bytes: int
    created_at: datetime
    expires_at: datetime
