"""Identity domain models for users, profiles, and registration allowlists.

Purpose:
  Keep framework-agnostic identity state in one place, including the
  allowlist/blocklist records used by registration domain validation.

Relationships:
  - Consumed by application handlers and repository protocols.
  - Mapped from SQLAlchemy models in `skriptoteket.infrastructure.db.models.*`.
  - Realm-aware external identity mappings live in
    `skriptoteket.domain.identity.projections`.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
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


class OrganizationType(StrEnum):
    KOMMUN = "kommun"
    ENSKILD_HUVUDMAN = "enskild_huvudman"
    GOVERNMENT_AGENCY = "government_agency"
    OTHER = "other"


class AllowedDomain(BaseModel):
    """A root domain allowed for automatic user registration."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    domain: str  # e.g., "stockholm.se"
    org_type: OrganizationType
    org_name: str
    source: str
    source_ref: str | None = None
    is_active: bool = True
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class BlockedDomain(BaseModel):
    """A root domain explicitly blocked (e.g., personal email providers)."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    domain: str  # e.g., "gmail.com"
    reason: str | None = None
    source: str
    source_ref: str | None = None
    is_active: bool = True
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    """Identity used across the application.

    `auth_provider` records which authority created the local user state.
    Realm-aware external subjects are stored in identity projections, not here.
    Authorization (role) remains local to Skriptoteket.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    email: str
    role: Role
    auth_provider: AuthProvider
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
    inline_completion_provider: Literal["local", "external"] | None = None
    classroom_planner_smart_enabled: bool | None = None
    classroom_planner_use_history: bool | None = None
    classroom_planner_grouping_seating_distance_enabled: bool | None = None
    locale: str = "sv-SE"
    created_at: datetime
    updated_at: datetime


class UserAuth(BaseModel):
    """Authentication material for login flows (kept separate from general User usage)."""

    model_config = ConfigDict(frozen=True)

    user: User
    password_hash: str | None = None
