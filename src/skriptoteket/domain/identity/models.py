from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    USER = "user"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class AuthProvider(StrEnum):
    LOCAL = "local"
    HULEEDU = "huleedu"


class User(BaseModel):
    """Identity used across the application.

    For future federation, `external_id` and `auth_provider` are included.
    Authorization (role) remains local to Skriptoteket.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    email: str
    role: Role
    auth_provider: AuthProvider
    external_id: str | None = None
    is_active: bool = True
    email_verified: bool = False
    failed_login_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    last_failed_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserProfile(BaseModel):
    """User profile data aligned with HuleEdu identity expectations."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    allow_remote_fallback: bool | None = None
    locale: str = "sv-SE"
    created_at: datetime
    updated_at: datetime


class UserAuth(BaseModel):
    """Authentication material for login flows (kept separate from general User usage)."""

    model_config = ConfigDict(frozen=True)

    user: User
    password_hash: str | None = None


class Session(BaseModel):
    """Server-side session stored in PostgreSQL."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID
    csrf_token: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
