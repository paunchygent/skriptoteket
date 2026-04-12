"""Realm-aware identity projection domain models.

Purpose:
    Represent the explicit mapping between a signed HuleEdu product identity
    realm subject and Skriptoteket-local user/profile/RBAC state.

Relationships:
    - Consumed by the HuleEdu app projection resolver and repository protocols.
    - Persisted by SQLAlchemy models in `skriptoteket.infrastructure.db.models`.
    - Keeps external realm subjects out of the `users` table.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductIdentityRealm(StrEnum):
    """HuleEdu product identity realms accepted by Skriptoteket."""

    SKRIPTOTEKET_STANDALONE = "skriptoteket_standalone"
    HULEEDU_SCHOOL = "huleedu_school"


class IdentityProjection(BaseModel):
    """Local projection from one product realm subject to one Skriptoteket user."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    user_id: UUID
    product_identity_realm: ProductIdentityRealm
    realm_subject_id: str
    created_at: datetime
    updated_at: datetime


class IdentityProjectionEventType(StrEnum):
    """Audit event names for projection resolution and provisioning outcomes."""

    RESOLVED = "resolved"
    PROVISIONED = "provisioned"
    BLOCKED_PROVISIONING = "blocked_provisioning"
    DUPLICATE_EMAIL_LINKING_REQUIRED = "duplicate_email_linking_required"
    UNSUPPORTED_REALM = "unsupported_realm"
    MIGRATION_BACKFILLED = "migration_backfilled"
    MIGRATION_BLOCKED = "migration_blocked"


class IdentityProjectionEvent(BaseModel):
    """Audit record for identity projection lookup, provisioning, and migration outcomes."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    id: UUID
    event_type: IdentityProjectionEventType
    user_id: UUID | None = None
    projection_id: UUID | None = None
    product_identity_realm: ProductIdentityRealm | None = None
    realm_subject_id: str | None = None
    reason_code: str
    correlation_id: UUID | None = None
    context_jti: str | None = None
    created_at: datetime
