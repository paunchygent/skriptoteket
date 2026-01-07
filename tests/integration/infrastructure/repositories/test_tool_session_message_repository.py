from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.tool_session_message_repository import (
    PostgreSQLToolSessionMessageRepository,
)
from skriptoteket.infrastructure.repositories.tool_session_repository import (
    PostgreSQLToolSessionRepository,
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
            email=f"tool-session-message-{uid.hex[:8]}@example.com",
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
            slug=f"chat-message-tool-{tid.hex[:8]}",
            title="Chat Message Tool",
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
async def test_append_and_list_tail_orders_oldest_to_newest(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionMessageRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    await repo.append_message(
        tool_session_id=session_id,
        message_id=uuid4(),
        role="user",
        content="First",
    )
    await repo.append_message(
        tool_session_id=session_id,
        message_id=uuid4(),
        role="assistant",
        content="Second",
    )
    await repo.append_message(
        tool_session_id=session_id,
        message_id=uuid4(),
        role="user",
        content="Third",
    )

    tail = await repo.list_tail(tool_session_id=session_id, limit=2)
    assert [message.content for message in tail] == ["Second", "Third"]


@pytest.mark.integration
async def test_get_by_message_id_returns_message_or_none(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionMessageRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    missing = await repo.get_by_message_id(tool_session_id=session_id, message_id=uuid4())
    assert missing is None

    message_id = uuid4()
    await repo.append_message(
        tool_session_id=session_id,
        message_id=message_id,
        role="user",
        content="Hello",
    )
    found = await repo.get_by_message_id(tool_session_id=session_id, message_id=message_id)
    assert found is not None
    assert found.message_id == message_id


@pytest.mark.integration
async def test_delete_all_removes_messages(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    repo = PostgreSQLToolSessionMessageRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    await repo.append_message(
        tool_session_id=session_id,
        message_id=uuid4(),
        role="user",
        content="Hello",
    )
    await repo.append_message(
        tool_session_id=session_id,
        message_id=uuid4(),
        role="assistant",
        content="World",
    )

    deleted = await repo.delete_all(tool_session_id=session_id)
    assert deleted == 2
    remaining = await repo.list_tail(tool_session_id=session_id, limit=10)
    assert remaining == []
