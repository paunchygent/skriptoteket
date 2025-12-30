from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import ResendVerificationCommand
from skriptoteket.application.identity.handlers.resend_verification import (
    RESEND_RATE_LIMIT_SECONDS,
    ResendVerificationHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.domain.identity.models import UserAuth, UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import (
    EmailMessage,
    EmailSenderProtocol,
    EmailTemplateRendererProtocol,
)
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol, UserRepositoryProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_resend_verification_creates_token_and_sends_email(now: datetime) -> None:
    """Resend verification should create a new token and send email."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": False})
    user_auth = UserAuth(user=user, password_hash="hash")
    profile = UserProfile(
        user_id=user.id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    token_id = uuid4()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_latest_by_user_id.return_value = None  # No recent token

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = token_id

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "new-verification-token"

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(ResendVerificationCommand(email="teacher@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_awaited_once()
    created_token = verification_tokens.create.call_args.kwargs["token"]
    assert created_token.user_id == user.id
    assert created_token.token == "new-verification-token"
    email_sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_resend_verification_returns_success_for_unknown_email(now: datetime) -> None:
    """Resend verification should return success even for unknown email (security)."""
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None  # User not found

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(ResendVerificationCommand(email="unknown@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_resend_verification_returns_success_for_verified_user(now: datetime) -> None:
    """Resend verification should return success for already verified user (security)."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": True})
    user_auth = UserAuth(user=user, password_hash="hash")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(ResendVerificationCommand(email="teacher@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_resend_verification_rate_limited(now: datetime) -> None:
    """Resend verification should silently skip if recent token exists."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": False})
    user_auth = UserAuth(user=user, password_hash="hash")

    # Token created 30 seconds ago (within rate limit window)
    existing_token = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="existing-token",
        expires_at=now + timedelta(hours=24),
        verified_at=None,
        created_at=now - timedelta(seconds=30),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = None

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_latest_by_user_id.return_value = existing_token

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(ResendVerificationCommand(email="teacher@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_resend_verification_allows_after_rate_limit_window(now: datetime) -> None:
    """Resend verification should allow new token after rate limit window."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": False})
    user_auth = UserAuth(user=user, password_hash="hash")
    profile = UserProfile(
        user_id=user.id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    # Token created 120 seconds ago (outside rate limit window)
    existing_token = EmailVerificationToken(
        id=uuid4(),
        user_id=user.id,
        token="existing-token",
        expires_at=now + timedelta(hours=24),
        verified_at=None,
        created_at=now - timedelta(seconds=RESEND_RATE_LIMIT_SECONDS + 60),
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_latest_by_user_id.return_value = existing_token

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "new-verification-token"

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(ResendVerificationCommand(email="teacher@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_awaited_once()
    email_sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_resend_verification_normalizes_email(now: datetime) -> None:
    """Resend verification should normalize email (strip and lowercase)."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": False})
    user_auth = UserAuth(user=user, password_hash="hash")
    profile = UserProfile(
        user_id=user.id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_latest_by_user_id.return_value = None

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "new-verification-token"

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    # Use mixed case with whitespace
    await handler.handle(ResendVerificationCommand(email="  Teacher@Example.COM  "))

    users.get_auth_by_email.assert_awaited_once_with("teacher@example.com")


@pytest.mark.asyncio
async def test_resend_verification_handles_email_failure_gracefully(now: datetime) -> None:
    """Resend verification should handle email sending failure gracefully."""
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": False})
    user_auth = UserAuth(user=user, password_hash="hash")
    profile = UserProfile(
        user_id=user.id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = user_auth

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    verification_tokens.get_latest_by_user_id.return_value = None

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_sender.send.side_effect = Exception("SMTP connection failed")

    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "new-verification-token"

    handler = ResendVerificationHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    # Should not raise - email failure is logged but not propagated
    result = await handler.handle(ResendVerificationCommand(email="teacher@example.com"))

    assert result.message == "Om kontot finns skickas ett nytt verifieringsmail"
    verification_tokens.create.assert_awaited_once()
    email_sender.send.assert_awaited_once()
