from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import Role, User


class LoginCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str


class LoginResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: UUID
    csrf_token: str
    user: User


class LogoutCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: UUID


class CreateLocalUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str
    role: Role


class CreateLocalUserResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
