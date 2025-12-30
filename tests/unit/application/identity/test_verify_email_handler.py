from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import VerifyEmailCommand
from skriptoteket.application.identity.handlers.verify_email import VerifyEmailHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_verify_email_succeeds_with_valid_token(now: datetime) -> None:
    """Verify email should mark token as used and set email_verified=True."""
    user = make_user(email="teacher@example.com")
    token_record = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="valid-token",
        expires_at=now + timedelta(hours=24),
        verified_at=None,
        created_at=now - timedelta(hours=1),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_by_token.return_value = token_record

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    updated_user = user.model_copy(update={"email_verified": True, "updated_at": now})
    users.update.return_value = updated_user

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    result = await handler.handle(VerifyEmailCommand(token="valid-token"))

    assert result.user.email_verified is True
    verification_tokens.mark_verified.assert_awaited_once_with(
        token_id=token_record.id,
        verified_at=now,
    )
    users.update.assert_awaited_once()
    verification_tokens.invalidate_all_for_user.assert_awaited_once_with(user_id=user.id)


@pytest.mark.asyncio
async def test_verify_email_raises_for_invalid_token(now: datetime) -> None:
    """Verify email should raise INVALID_VERIFICATION_TOKEN for unknown token."""
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_by_token.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(VerifyEmailCommand(token="invalid-token"))

    assert exc_info.value.code == ErrorCode.INVALID_VERIFICATION_TOKEN
    verification_tokens.mark_verified.assert_not_awaited()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email_raises_for_already_used_token(now: datetime) -> None:
    """Verify email should raise INVALID_VERIFICATION_TOKEN for already used token."""
    user = make_user(email="teacher@example.com")
    token_record = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="used-token",
        expires_at=now + timedelta(hours=24),
        verified_at=now - timedelta(hours=1),  # Already verified
        created_at=now - timedelta(hours=2),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_by_token.return_value = token_record

    users = AsyncMock(spec=UserRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(VerifyEmailCommand(token="used-token"))

    assert exc_info.value.code == ErrorCode.INVALID_VERIFICATION_TOKEN
    verification_tokens.mark_verified.assert_not_awaited()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email_raises_for_expired_token(now: datetime) -> None:
    """Verify email should raise VERIFICATION_TOKEN_EXPIRED for expired token."""
    user = make_user(email="teacher@example.com")
    token_record = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="expired-token",
        expires_at=now - timedelta(hours=1),  # Expired
        verified_at=None,
        created_at=now - timedelta(hours=25),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_by_token.return_value = token_record

    users = AsyncMock(spec=UserRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(VerifyEmailCommand(token="expired-token"))

    assert exc_info.value.code == ErrorCode.VERIFICATION_TOKEN_EXPIRED
    verification_tokens.mark_verified.assert_not_awaited()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email_raises_for_user_not_found(now: datetime) -> None:
    """Verify email should raise USER_NOT_FOUND if user was deleted."""
    user_id = uuid4()
    token_record = EmailVerificationToken(
        id=uuid4(),
        user_id=user_id,
        token="valid-token",
        expires_at=now + timedelta(hours=24),
        verified_at=None,
        created_at=now - timedelta(hours=1),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_by_token.return_value = token_record

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = None  # User was deleted

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(VerifyEmailCommand(token="valid-token"))

    assert exc_info.value.code == ErrorCode.USER_NOT_FOUND
    verification_tokens.mark_verified.assert_awaited_once()
    users.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_verify_email_enters_uow_before_token_lookup(now: datetime) -> None:
    """Verify email should enter UoW before fetching token."""
    events: list[str] = []

    user = make_user(email="teacher@example.com")
    token_record = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="valid-token",
        expires_at=now + timedelta(hours=24),
        verified_at=None,
        created_at=now - timedelta(hours=1),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)

    async def enter():
        events.append("uow_enter")
        return uow

    uow.__aenter__.side_effect = enter
    uow.__aexit__.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)

    async def get_by_token(_token: str):
        events.append("get_by_token")
        return token_record

    verification_tokens.get_by_token.side_effect = get_by_token

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = user
    users.update.return_value = user.model_copy(update={"email_verified": True, "updated_at": now})

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    handler = VerifyEmailHandler(
        uow=uow,
        users=users,
        verification_tokens=verification_tokens,
        clock=clock,
    )

    await handler.handle(VerifyEmailCommand(token="valid-token"))

    assert events[0] == "uow_enter"
    assert events[1] == "get_by_token"
