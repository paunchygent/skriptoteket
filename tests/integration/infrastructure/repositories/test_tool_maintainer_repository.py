from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel  # noqa: F401
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def owner_id(db_session: AsyncSession, now: datetime) -> UUID:
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"owner-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.ADMIN,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.fixture
async def tool_id(db_session: AsyncSession, owner_id: UUID, now: datetime) -> UUID:
    tid = uuid4()
    db_session.add(
        ToolModel(
            id=tid,
            owner_user_id=owner_id,
            slug=f"maint-test-{tid.hex[:8]}",
            title="Maintainer Test Tool",
            summary="For testing",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tid


async def _create_user(db_session: AsyncSession, now: datetime) -> UUID:
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"user-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.CONTRIBUTOR,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.mark.integration
async def test_add_and_is_maintainer(
    db_session: AsyncSession, tool_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user_id = await _create_user(db_session, now)

    # Initially not a maintainer
    assert await repo.is_maintainer(tool_id=tool_id, user_id=user_id) is False

    # Add as maintainer
    await repo.add_maintainer(tool_id=tool_id, user_id=user_id)

    # Now is a maintainer
    assert await repo.is_maintainer(tool_id=tool_id, user_id=user_id) is True


@pytest.mark.integration
async def test_add_maintainer_idempotent(
    db_session: AsyncSession, tool_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user_id = await _create_user(db_session, now)

    # Add twice - should not raise
    await repo.add_maintainer(tool_id=tool_id, user_id=user_id)
    await repo.add_maintainer(tool_id=tool_id, user_id=user_id)

    # Still just one maintainer entry
    maintainers = await repo.list_maintainers(tool_id=tool_id)
    assert maintainers.count(user_id) == 1


@pytest.mark.integration
async def test_list_maintainers(db_session: AsyncSession, tool_id: UUID, now: datetime) -> None:
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user1 = await _create_user(db_session, now)
    user2 = await _create_user(db_session, now)

    await repo.add_maintainer(tool_id=tool_id, user_id=user1)
    await repo.add_maintainer(tool_id=tool_id, user_id=user2)

    maintainers = await repo.list_maintainers(tool_id=tool_id)
    assert len(maintainers) == 2
    assert user1 in maintainers
    assert user2 in maintainers


@pytest.mark.integration
async def test_remove_maintainer(db_session: AsyncSession, tool_id: UUID, now: datetime) -> None:
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user_id = await _create_user(db_session, now)

    await repo.add_maintainer(tool_id=tool_id, user_id=user_id)
    assert await repo.is_maintainer(tool_id=tool_id, user_id=user_id) is True

    await repo.remove_maintainer(tool_id=tool_id, user_id=user_id)
    assert await repo.is_maintainer(tool_id=tool_id, user_id=user_id) is False


@pytest.mark.integration
async def test_remove_maintainer_nonexistent(
    db_session: AsyncSession, tool_id: UUID, now: datetime
) -> None:
    """Removing non-existent maintainer should not raise."""
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user_id = await _create_user(db_session, now)

    # Should not raise
    await repo.remove_maintainer(tool_id=tool_id, user_id=user_id)


@pytest.mark.integration
async def test_list_tools_for_user(db_session: AsyncSession, owner_id: UUID, now: datetime) -> None:
    repo = PostgreSQLToolMaintainerRepository(db_session)

    user_id = await _create_user(db_session, now)

    # Create two tools
    tool1 = uuid4()
    tool2 = uuid4()
    for tid in [tool1, tool2]:
        db_session.add(
            ToolModel(
                id=tid,
                owner_user_id=owner_id,
                slug=f"list-test-{tid.hex[:8]}",
                title="List Test Tool",
                summary="For testing",
                created_at=now,
                updated_at=now,
            )
        )
    await db_session.flush()

    await repo.add_maintainer(tool_id=tool1, user_id=user_id)
    await repo.add_maintainer(tool_id=tool2, user_id=user_id)

    tools = await repo.list_tools_for_user(user_id=user_id)
    assert len(tools) == 2
    assert tool1 in tools
    assert tool2 in tools
