from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.identity.models import AuthProvider, Role, User, UserProfile


class LoginCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    email: str
    password: str
    ip_address: str | None = None
    user_agent: str | None = None
    correlation_id: UUID | None = None
    auth_provider: AuthProvider = AuthProvider.LOCAL


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
    """Result after registration - no session, user must verify email."""

    model_config = ConfigDict(frozen=True)

    user: User
    profile: UserProfile
    verification_email_sent: bool = True


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


class UpdateAiSettingsCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_id: UUID
    remote_fallback_preference: Literal["unset", "allow", "deny"]


class UpdateAiSettingsResult(BaseModel):
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


class VerifyEmailCommand(BaseModel):
    """Command to verify email with token."""

    model_config = ConfigDict(frozen=True)

    token: str


class VerifyEmailResult(BaseModel):
    """Result of successful email verification."""

    model_config = ConfigDict(frozen=True)

    user: User
    message: str = "E-postadressen har verifierats"


class ResendVerificationCommand(BaseModel):
    """Command to resend verification email."""

    model_config = ConfigDict(frozen=True)

    email: str


class ResendVerificationResult(BaseModel):
    """Result of resend request (always success for security)."""

    model_config = ConfigDict(frozen=True)

    message: str = "Om kontot finns skickas ett nytt verifieringsmail"
