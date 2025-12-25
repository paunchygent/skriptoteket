from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import Role, User, UserProfile


class LoginCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str


class LoginResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: UUID
    csrf_token: str
    user: User
    profile: UserProfile | None = None


class LogoutCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: UUID
    csrf_token: str


class CreateLocalUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str
    role: Role


class CreateLocalUserResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User


class RegisterUserCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str
    first_name: str
    last_name: str


class RegisterUserResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: UUID
    csrf_token: str
    user: User
    profile: UserProfile


class GetProfileCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID


class GetProfileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile


class UpdateProfileCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    locale: str | None = None


class UpdateProfileResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile


class ChangePasswordCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    current_password: str
    new_password: str


class ChangeEmailCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    new_email: str


class ChangeEmailResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
