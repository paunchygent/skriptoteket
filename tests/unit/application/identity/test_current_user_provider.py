from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.current_user_provider import CurrentUserProvider
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import SessionRepositoryProtocol, UserRepositoryProtocol
from tests.fixtures.identity_fixtures import make_session, make_user


@pytest.mark.asyncio
async def test_get_current_user_returns_none_when_no_session_id() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)

    provider = CurrentUserProvider(users=users, sessions=sessions, clock=clock)
    assert await provider.get_current_user(session_id=None) is None


@pytest.mark.asyncio
async def test_get_current_user_returns_none_when_session_revoked(now: datetime) -> None:
    user = make_user()
    session_id = uuid4()
    session = make_session(session_id=session_id, user_id=user.id, now=now, revoked=True)

    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    sessions.get_by_id.return_value = session
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    provider = CurrentUserProvider(users=users, sessions=sessions, clock=clock)
    assert await provider.get_current_user(session_id=session_id) is None


@pytest.mark.asyncio
async def test_get_current_user_returns_none_when_session_expired(now: datetime) -> None:
    user = make_user()
    session_id = uuid4()
    session = make_session(
        session_id=session_id,
        user_id=user.id,
        now=now,
        expires_in=timedelta(seconds=0),
        revoked=False,
    )

    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    sessions.get_by_id.return_value = session
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    provider = CurrentUserProvider(users=users, sessions=sessions, clock=clock)
    assert await provider.get_current_user(session_id=session_id) is None


@pytest.mark.asyncio
async def test_get_current_user_returns_none_when_user_inactive(now: datetime) -> None:
    user = make_user()
    inactive_user = user.model_copy(update={"is_active": False})
    session_id = uuid4()
    session = make_session(session_id=session_id, user_id=inactive_user.id, now=now)

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = inactive_user
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    sessions.get_by_id.return_value = session
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    provider = CurrentUserProvider(users=users, sessions=sessions, clock=clock)
    assert await provider.get_current_user(session_id=session_id) is None


@pytest.mark.asyncio
async def test_get_current_user_returns_user_when_valid(now: datetime) -> None:
    user = make_user()
    session_id = uuid4()
    session = make_session(session_id=session_id, user_id=user.id, now=now)

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    sessions.get_by_id.return_value = session
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    provider = CurrentUserProvider(users=users, sessions=sessions, clock=clock)
    assert await provider.get_current_user(session_id=session_id) == user
