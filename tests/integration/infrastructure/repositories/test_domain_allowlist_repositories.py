from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import (
    AllowedDomain,
    BlockedDomain,
    OrganizationType,
)
from skriptoteket.infrastructure.repositories.allowed_domain_repository import (
    PostgreSQLAllowedDomainRepository,
)
from skriptoteket.infrastructure.repositories.blocked_domain_repository import (
    PostgreSQLBlockedDomainRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.integration
async def test_allowed_domain_repository_upsert_and_get(db_session: AsyncSession) -> None:
    repo = PostgreSQLAllowedDomainRepository(db_session)
    now = datetime.now(timezone.utc)

    created = await repo.upsert(
        domain=AllowedDomain(
            domain="harryda.se",
            org_type=OrganizationType.KOMMUN,
            org_name="Härryda kommun",
            source="skr_kommunlista",
            source_ref="https://www.harryda.se/",
            is_active=True,
            notes=None,
            created_at=now,
            updated_at=now,
        )
    )

    assert created.domain == "harryda.se"
    assert created.org_type == OrganizationType.KOMMUN

    updated = await repo.upsert(
        domain=created.model_copy(
            update={
                "org_name": "Härryda kommun uppdaterad",
                "notes": "manual correction",
                "updated_at": datetime.now(timezone.utc),
            }
        )
    )
    fetched = await repo.get_by_domain("harryda.se")

    assert updated.org_name == "Härryda kommun uppdaterad"
    assert fetched is not None
    assert fetched.org_name == "Härryda kommun uppdaterad"
    assert fetched.notes == "manual correction"


@pytest.mark.integration
async def test_blocked_domain_repository_upsert_and_list(db_session: AsyncSession) -> None:
    repo = PostgreSQLBlockedDomainRepository(db_session)
    now = datetime.now(timezone.utc)

    await repo.upsert(
        domain=BlockedDomain(
            domain="gmail.com",
            reason="personal_email_provider",
            source="manual_seed",
            source_ref="common_provider_seed",
            is_active=True,
            notes=None,
            created_at=now,
            updated_at=now,
        )
    )
    await repo.upsert(
        domain=BlockedDomain(
            domain="hotmail.com",
            reason="personal_email_provider",
            source="manual_seed",
            source_ref="common_provider_seed",
            is_active=False,
            notes="disabled for test",
            created_at=now,
            updated_at=now,
        )
    )

    listed = await repo.list_all()

    assert [row.domain for row in listed] == ["gmail.com", "hotmail.com"]
    assert listed[1].is_active is False
