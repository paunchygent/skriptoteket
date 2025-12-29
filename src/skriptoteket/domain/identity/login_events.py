from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import AuthProvider


class LoginEventStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


class LoginEvent(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID | None
    status: LoginEventStatus
    failure_code: str | None
    ip_address: str | None
    user_agent: str | None
    auth_provider: AuthProvider
    correlation_id: UUID | None
    geo_country_code: str | None
    geo_region: str | None
    geo_city: str | None
    geo_latitude: float | None
    geo_longitude: float | None
    created_at: datetime
