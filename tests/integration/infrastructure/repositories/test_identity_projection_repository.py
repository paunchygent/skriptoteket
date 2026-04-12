"""Integration tests for identity projection repositories.

Purpose:
    Prove the repository layer stores realm-aware projection keys and audit
    events without relying on legacy user-level provider subjects.

Relationships:
    - Covers `PostgreSQLIdentityProjectionRepository`.
    - Uses `PostgreSQLUserRepository` to seed local Skriptoteket user state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.identity.projections import (
    IdentityProjection,
    IdentityProjectionEvent,
    IdentityProjectionEventType,
    ProductIdentityRealm,
)
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_identity_projection_repository_crud_and_audit(
    db_session: AsyncSession,
) -> None:
    users = PostgreSQLUserRepository(db_session)
    projections = PostgreSQLIdentityProjectionRepository(db_session)
    events = PostgreSQLIdentityProjectionEventRepository(db_session)
    now = datetime.now(timezone.utc)
    user = await users.create(
        user=User(
            id=uuid.uuid4(),
            email="projection-repo@example.test",
            role=Role.USER,
            auth_provider=AuthProvider.HULEEDU,
            is_active=True,
            email_verified=True,
            created_at=now,
            updated_at=now,
        ),
        password_hash=None,
    )

    projection = await projections.create(
        projection=IdentityProjection(
            id=uuid.uuid4(),
            user_id=user.id,
            product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
            realm_subject_id="realm-subject-1",
            created_at=now,
            updated_at=now,
        )
    )
    await events.create(
        event=IdentityProjectionEvent(
            id=uuid.uuid4(),
            event_type=IdentityProjectionEventType.PROVISIONED,
            user_id=user.id,
            projection_id=projection.id,
            product_identity_realm=ProductIdentityRealm.SKRIPTOTEKET_STANDALONE,
            realm_subject_id="realm-subject-1",
            reason_code="projection_provisioned",
            correlation_id=None,
            context_jti="ctx-integration-1",
            created_at=now,
        )
    )

    fetched = await projections.get_by_realm_subject(
        product_identity_realm="skriptoteket_standalone",
        realm_subject_id="realm-subject-1",
    )

    assert fetched == projection
