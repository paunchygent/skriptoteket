from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import RequestPasswordResetCommand
from skriptoteket.application.identity.handlers.request_password_reset import (
    RequestPasswordResetHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import AuthProvider, UserAuth, UserProfile
from skriptoteket.domain.identity.password_reset import hash_password_reset_token
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import (
    EmailMessage,
    EmailSenderProtocol,
    EmailTemplateRendererProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.password_reset import (
    PasswordResetRequestThrottleProtocol,
    PasswordResetTokenRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_request_password_reset_creates_token_and_sends_email(now: datetime) -> None:
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(update={"email_verified": True})

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = UserAuth(user=user, password_hash="hash")

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = UserProfile(
        user_id=user.id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )

    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_throttle = Mock(spec=PasswordResetRequestThrottleProtocol)
    password_reset_throttle.is_rate_limited.return_value = False

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email=user.email,
        subject="Återställ ditt lösenord",
        html_body="<html>reset</html>",
        text_body="reset",
    )

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "reset-token"

    handler = RequestPasswordResetHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        password_reset_tokens=password_reset_tokens,
        password_reset_throttle=password_reset_throttle,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(RequestPasswordResetCommand(email="Teacher@Example.com"))

    assert result.message == "Om kontot kan återställas skickas en återställningslänk."
    password_reset_throttle.record_request.assert_called_once_with(
        normalized_email="teacher@example.com",
        now=now,
    )
    password_reset_tokens.invalidate_pending_for_user.assert_awaited_once_with(
        user_id=user.id,
        used_at=now,
    )
    password_reset_tokens.create.assert_awaited_once()
    created_token = password_reset_tokens.create.await_args.kwargs["token"]
    assert created_token.user_id == user.id
    assert created_token.token_hash == hash_password_reset_token(token="reset-token")
    assert created_token.expires_at == now + timedelta(hours=settings.PASSWORD_RESET_TTL_HOURS)
    email_sender.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_password_reset_returns_generic_success_for_unknown_email(
    now: datetime,
) -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_throttle = Mock(spec=PasswordResetRequestThrottleProtocol)
    password_reset_throttle.is_rate_limited.return_value = False
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RequestPasswordResetHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        password_reset_tokens=password_reset_tokens,
        password_reset_throttle=password_reset_throttle,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(RequestPasswordResetCommand(email="missing@example.com"))

    assert result.message == "Om kontot kan återställas skickas en återställningslänk."
    password_reset_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_password_reset_returns_generic_success_for_ineligible_user(
    now: datetime,
) -> None:
    settings = Settings()
    user = make_user(email="teacher@example.com").model_copy(
        update={"email_verified": False, "auth_provider": AuthProvider.LOCAL}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = UserAuth(user=user, password_hash="hash")

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_throttle = Mock(spec=PasswordResetRequestThrottleProtocol)
    password_reset_throttle.is_rate_limited.return_value = False
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RequestPasswordResetHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        password_reset_tokens=password_reset_tokens,
        password_reset_throttle=password_reset_throttle,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(RequestPasswordResetCommand(email=user.email))

    assert result.message == "Om kontot kan återställas skickas en återställningslänk."
    password_reset_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_password_reset_returns_generic_success_when_rate_limited(
    now: datetime,
) -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    password_reset_tokens = AsyncMock(spec=PasswordResetTokenRepositoryProtocol)
    password_reset_throttle = Mock(spec=PasswordResetRequestThrottleProtocol)
    password_reset_throttle.is_rate_limited.return_value = True
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now
    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RequestPasswordResetHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        password_reset_tokens=password_reset_tokens,
        password_reset_throttle=password_reset_throttle,
        email_sender=email_sender,
        email_renderer=email_renderer,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(RequestPasswordResetCommand(email="teacher@example.com"))

    assert result.message == "Om kontot kan återställas skickas en återställningslänk."
    password_reset_throttle.record_request.assert_not_called()
    users.get_auth_by_email.assert_not_awaited()
    password_reset_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()
