from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
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
async def test_list_by_turn_ids_returns_messages_ordered_by_turn_then_role(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    turn_1 = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="complete",
        provider="primary",
        correlation_id=None,
    )
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn_1.id,
        message_id=uuid4(),
        role="user",
        content="First",
    )
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn_1.id,
        message_id=uuid4(),
        role="assistant",
        content="Second",
    )

    turn_2 = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="complete",
        provider="primary",
        correlation_id=None,
    )
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn_2.id,
        message_id=uuid4(),
        role="user",
        content="Third",
    )
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn_2.id,
        message_id=uuid4(),
        role="assistant",
        content="Fourth",
    )

    tail_turns = await turns.list_tail(tool_session_id=session_id, limit=1)
    assert [turn.id for turn in tail_turns] == [turn_2.id]

    tail_messages = await messages.list_by_turn_ids(
        tool_session_id=session_id,
        turn_ids=[turn_2.id],
    )
    assert [message.role for message in tail_messages] == ["user", "assistant"]
    assert [message.content for message in tail_messages] == ["Third", "Fourth"]


@pytest.mark.integration
async def test_get_by_message_id_returns_message_or_none(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    missing = await messages.get_by_message_id(tool_session_id=session_id, message_id=uuid4())
    assert missing is None

    turn = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="complete",
        provider="primary",
        correlation_id=None,
    )
    message_id = uuid4()
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=message_id,
        role="user",
        content="Hello",
    )
    found = await messages.get_by_message_id(tool_session_id=session_id, message_id=message_id)
    assert found is not None
    assert found.message_id == message_id


@pytest.mark.integration
async def test_delete_all_removes_messages(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    turn = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="complete",
        provider="primary",
        correlation_id=None,
    )

    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=uuid4(),
        role="user",
        content="Hello",
    )
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=uuid4(),
        role="assistant",
        content="World",
    )

    deleted = await messages.delete_all(tool_session_id=session_id)
    assert deleted == 2
    remaining = await messages.list_by_turn_ids(tool_session_id=session_id, turn_ids=[turn.id])
    assert remaining == []


@pytest.mark.integration
async def test_update_message_content_if_pending_turn_updates_only_when_pending(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    correlation_id = uuid4()
    turn = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider="primary",
        correlation_id=correlation_id,
    )
    assistant_id = uuid4()
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=assistant_id,
        role="assistant",
        content="",
    )

    updated = await messages.update_message_content_if_pending_turn(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=assistant_id,
        content="partial",
        correlation_id=correlation_id,
    )
    assert updated is True

    await turns.update_status(
        turn_id=turn.id,
        status="complete",
        correlation_id=correlation_id,
        provider="primary",
    )

    blocked = await messages.update_message_content_if_pending_turn(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=assistant_id,
        content="later",
        correlation_id=correlation_id,
    )
    assert blocked is False


@pytest.mark.integration
async def test_update_message_content_if_pending_turn_requires_matching_correlation_id(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    correlation_id = uuid4()
    turn = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="pending",
        provider="primary",
        correlation_id=correlation_id,
    )
    assistant_id = uuid4()
    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=assistant_id,
        role="assistant",
        content="",
    )

    updated = await messages.update_message_content_if_pending_turn(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=assistant_id,
        content="partial",
        correlation_id=uuid4(),
    )
    assert updated is False


@pytest.mark.integration
async def test_turn_role_unique_constraint_is_enforced(
    db_session: AsyncSession, tool_id: UUID, user_id: UUID
) -> None:
    messages = PostgreSQLToolSessionMessageRepository(db_session)
    turns = PostgreSQLToolSessionTurnRepository(db_session)
    session_id = await _create_session(db_session=db_session, tool_id=tool_id, user_id=user_id)

    turn = await turns.create_turn(
        turn_id=uuid4(),
        tool_session_id=session_id,
        status="complete",
        provider="primary",
        correlation_id=None,
    )

    await messages.create_message(
        tool_session_id=session_id,
        turn_id=turn.id,
        message_id=uuid4(),
        role="user",
        content="First",
    )

    with pytest.raises(IntegrityError):
        await messages.create_message(
            tool_session_id=session_id,
            turn_id=turn.id,
            message_id=uuid4(),
            role="user",
            content="Second",
        )
    await db_session.rollback()
