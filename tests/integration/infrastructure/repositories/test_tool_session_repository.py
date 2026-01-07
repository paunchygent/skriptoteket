from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_session_repository import (
    PostgreSQLToolSessionRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    """Create a user for FK constraints."""
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"tool-session-test-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


@pytest.fixture
async def tool_id(db_session: AsyncSession, user_id: UUID, now: datetime) -> UUID:
    """Create a tool for FK constraints."""
    tid = uuid4()
    db_session.add(
        ToolModel(
            id=tid,
            owner_user_id=user_id,
            slug=f"session-test-tool-{tid.hex[:8]}",
            title="Session Test Tool",
            summary="For testing",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tid


@pytest.mark.integration
async def test_get_or_create_creates_new_session(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    session_id = uuid4()
    session = await repo.get_or_create(
        session_id=session_id,
        tool_id=tool_id,
        user_id=user_id,
        context="sandbox",
    )

    assert session.tool_id == tool_id
    assert session.user_id == user_id
    assert session.context == "sandbox"
    assert session.state == {}
    assert session.state_rev == 0


@pytest.mark.integration
async def test_get_or_create_returns_existing_session(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    # Create first session
    first_session = await repo.get_or_create(
        session_id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="production",
    )
    original_id = first_session.id

    # Try to create again with different session_id - should return existing
    second_session = await repo.get_or_create(
        session_id=uuid4(),  # Different ID
        tool_id=tool_id,
        user_id=user_id,
        context="production",
    )

    assert second_session.id == original_id  # Same session returned


@pytest.mark.integration
async def test_get_returns_none_for_nonexistent(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    session = await repo.get(
        tool_id=tool_id,
        user_id=user_id,
        context="nonexistent-context",
    )
    assert session is None


@pytest.mark.integration
async def test_update_state_persists_and_increments_rev(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    # Create session
    session = await repo.get_or_create(
        session_id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="update-test",
    )
    assert session.state_rev == 0

    # Update state
    updated = await repo.update_state(
        tool_id=tool_id,
        user_id=user_id,
        context="update-test",
        expected_state_rev=0,
        state={"key": "value", "count": 42},
    )

    assert updated.state == {"key": "value", "count": 42}
    assert updated.state_rev == 1

    # Verify persistence via get
    fetched = await repo.get(
        tool_id=tool_id,
        user_id=user_id,
        context="update-test",
    )
    assert fetched is not None
    assert fetched.state == {"key": "value", "count": 42}
    assert fetched.state_rev == 1


@pytest.mark.integration
async def test_update_state_optimistic_concurrency_conflict(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    # Create session
    await repo.get_or_create(
        session_id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="conflict-test",
    )

    # First update succeeds
    await repo.update_state(
        tool_id=tool_id,
        user_id=user_id,
        context="conflict-test",
        expected_state_rev=0,
        state={"first": True},
    )

    # Second update with stale rev fails
    with pytest.raises(DomainError) as exc:
        await repo.update_state(
            tool_id=tool_id,
            user_id=user_id,
            context="conflict-test",
            expected_state_rev=0,  # Stale rev
            state={"second": True},
        )

    assert exc.value.code == ErrorCode.CONFLICT
    assert "state_rev conflict" in exc.value.message


@pytest.mark.integration
async def test_update_state_raises_not_found(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    with pytest.raises(DomainError) as exc:
        await repo.update_state(
            tool_id=tool_id,
            user_id=user_id,
            context="nonexistent",
            expected_state_rev=0,
            state={"key": "value"},
        )

    assert exc.value.code == ErrorCode.NOT_FOUND


@pytest.mark.integration
async def test_clear_state_resets_to_empty_and_increments_rev(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    # Create session with state
    await repo.get_or_create(
        session_id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="clear-test",
    )
    await repo.update_state(
        tool_id=tool_id,
        user_id=user_id,
        context="clear-test",
        expected_state_rev=0,
        state={"data": "to-be-cleared"},
    )

    # Clear state
    cleared = await repo.clear_state(
        tool_id=tool_id,
        user_id=user_id,
        context="clear-test",
    )

    assert cleared.state == {}
    assert cleared.state_rev == 2  # Incremented from 1

    # Verify persistence
    fetched = await repo.get(
        tool_id=tool_id,
        user_id=user_id,
        context="clear-test",
    )
    assert fetched is not None
    assert fetched.state == {}
    assert fetched.state_rev == 2


@pytest.mark.integration
async def test_clear_state_raises_not_found(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionRepository(db_session)

    with pytest.raises(DomainError) as exc:
        await repo.clear_state(
            tool_id=tool_id,
            user_id=user_id,
            context="nonexistent",
        )

    assert exc.value.code == ErrorCode.NOT_FOUND
