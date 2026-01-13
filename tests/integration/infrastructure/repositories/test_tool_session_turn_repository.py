from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_session_repository import (
    PostgreSQLToolSessionRepository,
)
from skriptoteket.infrastructure.repositories.tool_session_turn_repository import (
    PostgreSQLToolSessionTurnRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"tool-session-turn-{uid.hex[:8]}@example.com",
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
    tid = uuid4()
    db_session.add(
        ToolModel(
            id=tid,
            owner_user_id=user_id,
            slug=f"chat-turn-tool-{tid.hex[:8]}",
            title="Chat Turn Tool",
            summary="For testing",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tid


async def _create_session(*, db_session: AsyncSession, tool_id: UUID, user_id: UUID) -> UUID:
    sessions = PostgreSQLToolSessionRepository(db_session)
    session = await sessions.get_or_create(
        session_id=uuid4(),
        tool_id=tool_id,
        user_id=user_id,
        context="editor_chat",
    )
    return session.id


@pytest.mark.integration
async def test_get_pending_turn_returns_latest_pending(
    db_session: AsyncSession,
    tool_id: UUID,
    user_id: UUID,
) -> None:
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    correlation_id = uuid4()
    pending = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider=None,
        correlation_id=correlation_id,
    )

    found = await turns.get_pending_turn(tool_session_id=session_id)
    assert found is not None
    assert found.id == pending.id
    assert found.status == "pending"


@pytest.mark.integration
async def test_update_status_requires_pending_and_respects_correlation_guard(
    db_session: AsyncSession,
    tool_id: UUID,
    user_id: UUID,
) -> None:
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    correlation_id = uuid4()
    pending = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider=None,
        correlation_id=correlation_id,
    )

    mismatched = await turns.update_status(
        turn_id=pending.id,
        status="complete",
        correlation_id=uuid4(),
        failure_outcome=None,
        provider="primary",
    )
    assert mismatched is None

    updated = await turns.update_status(
        turn_id=pending.id,
        status="complete",
        correlation_id=correlation_id,
        failure_outcome=None,
        provider="primary",
    )
    assert updated is not None
    assert updated.status == "complete"
    assert updated.provider == "primary"

    none_left = await turns.get_pending_turn(tool_session_id=session_id)
    assert none_left is None


@pytest.mark.integration
async def test_cancel_pending_turn_marks_cancelled(
    db_session: AsyncSession,
    tool_id: UUID,
    user_id: UUID,
) -> None:
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider=None,
        correlation_id=None,
    )

    cancelled = await turns.cancel_pending_turn(
        tool_session_id=session_id,
        failure_outcome="abandoned_by_new_request",
    )
    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert cancelled.failure_outcome == "abandoned_by_new_request"


@pytest.mark.integration
async def test_one_pending_turn_per_session_is_enforced(
    db_session: AsyncSession,
    tool_id: UUID,
    user_id: UUID,
) -> None:
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider=None,
        correlation_id=None,
    )

    with pytest.raises(IntegrityError):
        await turns.create_turn(
            turn_id=uuid4(),
            tool_session_id=session_id,
            status="pending",
            provider=None,
            correlation_id=None,
        )
    await db_session.rollback()
