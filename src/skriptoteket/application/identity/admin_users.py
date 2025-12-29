from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.identity.models import User


class ListUsersQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ListUsersResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    users: list[User]
    total: int


class GetUserQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID


class GetUserResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
