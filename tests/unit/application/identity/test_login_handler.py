from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import LoginCommand
from skriptoteket.application.identity.handlers.login import LoginHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.lockout import LOCKOUT_DURATION
from skriptoteket.domain.identity.models import UserAuth
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_login_creates_session_and_returns_user(now: datetime) -> None:
    settings = Settings()
    fixed_now = now
    user = make_user(email="teacher@example.com")
    user_auth = UserAuth(user=user, password_hash="hash")
    updated_user = user.model_copy(
        update={
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": fixed_now,
            "updated_at": fixed_now,
        }
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth
    users.update.return_value = updated_user

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = None

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.verify.return_value = True

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = fixed_now

    session_id = uuid4()
    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = session_id

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "csrf"

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(LoginCommand(email=" Teacher@Example.com ", password="pw"))

    assert result.session_id == session_id
    assert result.csrf_token == "csrf"
    assert result.user == updated_user

    sessions.create.assert_awaited_once()
    users.update.assert_awaited_once()
    created_session = sessions.create.call_args.kwargs["session"]
    assert created_session.user_id == user.id
    assert created_session.created_at == fixed_now
    assert created_session.expires_at == fixed_now + timedelta(seconds=settings.SESSION_TTL_SECONDS)


@pytest.mark.asyncio
async def test_login_raises_for_invalid_credentials() -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(LoginCommand(email="nope@example.com", password="pw"))

    assert exc_info.value.code == ErrorCode.INVALID_CREDENTIALS
    sessions.create.assert_not_awaited()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_enters_uow_before_reading_user_auth(now: datetime) -> None:
    events: list[str] = []

    settings = Settings()
    user = make_user(email="teacher@example.com")
    user_auth = UserAuth(user=user, password_hash="hash")

    uow = AsyncMock(spec=UnitOfWorkProtocol)

    async def enter():
        events.append("uow_enter")
        return uow

    uow.__aenter__.side_effect = enter
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)

    async def get_auth_by_email(email: str):
        events.append("users_get_auth_by_email")
        return user_auth

    users.get_auth_by_email.side_effect = get_auth_by_email

    async def update_user(*, user):
        events.append("users_update")
        return user

    users.update.side_effect = update_user

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    async def create_session(*, session):
        events.append("sessions_create")
        return None

    sessions.create.side_effect = create_session

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = None

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.verify.return_value = True

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "csrf"

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    await handler.handle(LoginCommand(email="teacher@example.com", password="pw"))

    assert events[0] == "uow_enter"


@pytest.mark.asyncio
async def test_login_locks_account_on_threshold(now: datetime) -> None:
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(
        update={
            "failed_login_attempts": 4,
            "locked_until": None,
            "updated_at": now,
        }
    )
    user_auth = UserAuth(user=user, password_hash="hash")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.verify.return_value = False

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(LoginCommand(email="teacher@example.com", password="pw"))

    assert exc_info.value.code == ErrorCode.ACCOUNT_LOCKED
    assert exc_info.value.details["retry_after_seconds"] == int(LOCKOUT_DURATION.total_seconds())

    users.update.assert_awaited_once()
    updated_user = users.update.call_args.kwargs["user"]
    assert updated_user.failed_login_attempts == 5
    assert updated_user.locked_until == now + LOCKOUT_DURATION
    sessions.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_rejects_when_already_locked(now: datetime) -> None:
    settings = Settings()
    locked_until = now + LOCKOUT_DURATION
    user = make_user(email="teacher@example.com").model_copy(update={"locked_until": locked_until})
    user_auth = UserAuth(user=user, password_hash="hash")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    sessions = AsyncMock(spec=SessionRepositoryProtocol)

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.verify.return_value = True

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = LoginHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        sessions=sessions,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(LoginCommand(email="teacher@example.com", password="pw"))

    assert exc_info.value.code == ErrorCode.ACCOUNT_LOCKED
    assert exc_info.value.details["retry_after_seconds"] == int(LOCKOUT_DURATION.total_seconds())
    password_hasher.verify.assert_not_called()
    users.update.assert_not_awaited()
    sessions.create.assert_not_awaited()
