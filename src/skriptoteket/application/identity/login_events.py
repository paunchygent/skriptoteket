from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.identity.login_events import LoginEvent


class ListLoginEventsQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    limit: int = Field(default=50, ge=1, le=200)


class ListLoginEventsResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    events: list[LoginEvent]
