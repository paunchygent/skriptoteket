from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import ResetPasswordCommand
from skriptoteket.application.identity.handlers.reset_password import ResetPasswordHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import AuthProvider
from skriptoteket.domain.identity.password_reset import (
    PasswordResetToken,
    hash_password_reset_token,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.password_reset import PasswordResetTokenRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_reset_password_updates_hash_and_revokes_all_sessions(now: datetime) -> None:
    user = make_user(email="teacher@example.com").model_copy(
        update={
            "email_verified": True,
            "failed_login_attempts": 4,
            "locked_until": now + timedelta(minutes=5),
            "last_failed_login_at": now - timedelta(minutes=1),
        }
    )
    token_record = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_password_reset_token(token="valid-token"),
        expires_at=now + timedelta(hours=2),
        used_at=None,
        created_at=now - timedelta(minutes=5),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user

    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = token_record

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "new-password-hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    result = await handler.handle(
        ResetPasswordCommand(token="valid-token", new_password="strong-password")
    )

    assert result.message == "Lösenordet har återställts. Logga in med ditt nya lösenord."
    users.update.assert_awaited_once()
    updated_user = users.update.await_args.kwargs["user"]
    assert updated_user.failed_login_attempts == 0
    assert updated_user.locked_until is None
    assert updated_user.last_failed_login_at is None
    users.update_password_hash.assert_awaited_once_with(
        user_id=user.id,
        password_hash="new-password-hash",
        updated_at=now,
    )
    sessions.revoke_all_for_user.assert_awaited_once_with(user_id=user.id, revoked_at=now)
    password_reset_tokens.mark_used.assert_awaited_once_with(token_id=token_record.id, used_at=now)
    password_reset_tokens.invalidate_pending_for_user.assert_awaited_once_with(
        user_id=user.id,
        used_at=now,
    )


@pytest.mark.asyncio
async def test_reset_password_raises_for_invalid_token(now: datetime) -> None:
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = None
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            ResetPasswordCommand(token="invalid-token", new_password="strong-pass")
        )

    assert exc_info.value.code == ErrorCode.INVALID_PASSWORD_RESET_TOKEN
    users.update.assert_not_awaited()
    sessions.revoke_all_for_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_password_raises_for_expired_token(now: datetime) -> None:
    user = make_user(email="teacher@example.com")
    token_record = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_password_reset_token(token="expired-token"),
        expires_at=now - timedelta(minutes=1),
        used_at=None,
        created_at=now - timedelta(hours=2),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = token_record
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            ResetPasswordCommand(token="expired-token", new_password="strong-pass")
        )

    assert exc_info.value.code == ErrorCode.PASSWORD_RESET_TOKEN_EXPIRED
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_password_raises_for_used_token(now: datetime) -> None:
    user = make_user(email="teacher@example.com")
    token_record = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_password_reset_token(token="used-token"),
        expires_at=now + timedelta(hours=1),
        used_at=now - timedelta(minutes=1),
        created_at=now - timedelta(hours=1),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = token_record
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ResetPasswordCommand(token="used-token", new_password="strong-pass"))

    assert exc_info.value.code == ErrorCode.INVALID_PASSWORD_RESET_TOKEN


@pytest.mark.asyncio
async def test_reset_password_raises_for_non_local_user(now: datetime) -> None:
    user = make_user(email="teacher@example.com").model_copy(
        update={"auth_provider": AuthProvider.HULEEDU}
    )
    token_record = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_password_reset_token(token="valid-token"),
        expires_at=now + timedelta(hours=1),
        used_at=None,
        created_at=now - timedelta(minutes=10),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = token_record
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ResetPasswordCommand(token="valid-token", new_password="strong-pass"))

    assert exc_info.value.code == ErrorCode.INVALID_PASSWORD_RESET_TOKEN


@pytest.mark.asyncio
async def test_reset_password_raises_for_weak_password(now: datetime) -> None:
    user = make_user(email="teacher@example.com")
    token_record = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=hash_password_reset_token(token="valid-token"),
        expires_at=now + timedelta(hours=1),
        used_at=None,
        created_at=now - timedelta(minutes=10),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    sessions = AsyncMock(spec=SessionRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_tokens.get_by_token_hash.return_value = token_record
    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = ResetPasswordHandler(
        uow=uow,
        users=users,
        sessions=sessions,
        password_reset_tokens=password_reset_tokens,
        password_hasher=password_hasher,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(ResetPasswordCommand(token="valid-token", new_password="short"))

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.update.assert_not_awaited()
    sessions.revoke_all_for_user.assert_not_awaited()
