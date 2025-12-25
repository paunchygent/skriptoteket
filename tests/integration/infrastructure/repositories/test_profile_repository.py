from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role, UserProfile
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.profile_repository import (
    PostgreSQLProfileRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    """Create a user for profile FK constraint."""
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"profile-test-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.mark.integration
async def test_profile_create_and_get(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLProfileRepository(db_session)

    profile = UserProfile(
        user_id=user_id,
        first_name="Anna",
        last_name="Andersson",
        display_name="Anna A.",
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    # Create
    created = await repo.create(profile=profile)
    assert created.user_id == user_id
    assert created.first_name == "Anna"
    assert created.last_name == "Andersson"
    assert created.display_name == "Anna A."
    assert created.locale == "sv-SE"

    # Get
    fetched = await repo.get_by_user_id(user_id=user_id)
    assert fetched is not None
    assert fetched.first_name == "Anna"
    assert fetched.last_name == "Andersson"
    assert fetched.display_name == "Anna A."
    assert fetched.locale == "sv-SE"


@pytest.mark.integration
async def test_profile_create_with_nulls(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLProfileRepository(db_session)

    profile = UserProfile(
        user_id=user_id,
        first_name=None,
        last_name=None,
        display_name=None,
        locale="en-US",
        created_at=now,
        updated_at=now,
    )

    created = await repo.create(profile=profile)
    assert created.first_name is None
    assert created.last_name is None
    assert created.display_name is None
    assert created.locale == "en-US"

    fetched = await repo.get_by_user_id(user_id=user_id)
    assert fetched is not None
    assert fetched.first_name is None
    assert fetched.last_name is None
    assert fetched.display_name is None


@pytest.mark.integration
async def test_profile_update(db_session: AsyncSession, user_id: UUID, now: datetime) -> None:
    repo = PostgreSQLProfileRepository(db_session)

    # Create initial profile
    profile = UserProfile(
        user_id=user_id,
        first_name="Old",
        last_name="Name",
        display_name="Old N.",
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    await repo.create(profile=profile)

    # Update
    updated_profile = profile.model_copy(
        update={
            "first_name": "New",
            "last_name": "Name",
            "display_name": "New N.",
            "locale": "en-GB",
        }
    )
    updated = await repo.update(profile=updated_profile)
    assert updated.first_name == "New"
    assert updated.last_name == "Name"
    assert updated.display_name == "New N."
    assert updated.locale == "en-GB"

    # Verify persistence
    fetched = await repo.get_by_user_id(user_id=user_id)
    assert fetched is not None
    assert fetched.first_name == "New"
    assert fetched.locale == "en-GB"


@pytest.mark.integration
async def test_profile_update_raises_not_found(db_session: AsyncSession, now: datetime) -> None:
    repo = PostgreSQLProfileRepository(db_session)

    missing_profile = UserProfile(
        user_id=uuid4(),
        first_name="Ghost",
        last_name="User",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(DomainError) as exc:
        await repo.update(profile=missing_profile)
    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.integration
async def test_profile_get_nonexistent(db_session: AsyncSession) -> None:
    repo = PostgreSQLProfileRepository(db_session)

    fetched = await repo.get_by_user_id(user_id=uuid4())
    assert fetched is None
