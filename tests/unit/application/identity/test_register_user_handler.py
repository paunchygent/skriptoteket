from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.identity.commands import RegisterUserCommand
from skriptoteket.application.identity.handlers.register_user import RegisterUserHandler
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.email_verification import EmailVerificationToken
from skriptoteket.domain.identity.models import UserProfile
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import (
    EmailMessage,
    EmailSenderProtocol,
    EmailTemplateRendererProtocol,
)
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_register_user_creates_profile_and_sends_verification_email(now: datetime) -> None:
    settings = Settings()
    user_id = uuid4()
    token_id = uuid4()
    created_user = make_user(email="teacher@example.com", user_id=user_id).model_copy(
        update={"created_at": now, "updated_at": now, "email_verified": False}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None
    users.create.return_value = created_user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    expected_profile = UserProfile(
        user_id=user_id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    profiles.create.return_value = expected_profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    expected_token = EmailVerificationToken(
        id=token_id,
        user_id=user_id,
        token="verification-token",
        expires_at=now + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
        verified_at=None,
        created_at=now,
    )
    verification_tokens.create.return_value = expected_token

    email_sender = AsyncMock(spec=EmailSenderProtocol)

    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [user_id, token_id]

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "verification-token"

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(
        RegisterUserCommand(
            email="Teacher@Example.com",
            password="password123",
            first_name=" Ada ",
            last_name=" Lovelace ",
        )
    )

    assert result.user == created_user
    assert result.profile == expected_profile
    assert result.verification_email_sent is True

    # Verify token was created
    verification_tokens.create.assert_awaited_once()
    created_token = verification_tokens.create.call_args.kwargs["token"]
    assert created_token.user_id == user_id
    assert created_token.token == "verification-token"
    assert created_token.expires_at == now + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS)

    # Verify email was sent
    email_sender.send.assert_awaited_once()
    email_renderer.render.assert_called_once()


@pytest.mark.asyncio
async def test_register_user_rejects_invalid_email(now: datetime) -> None:
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="not-an-email",
                password="password123",
                first_name="Ada",
                last_name="Lovelace",
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.get_auth_by_email.assert_not_awaited()
    users.create.assert_not_awaited()
    profiles.create.assert_not_awaited()
    verification_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_email(now: datetime) -> None:
    """Registration should fail if email is already registered."""
    settings = Settings()
    existing_user = make_user(email="teacher@example.com")

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    from skriptoteket.domain.identity.models import UserAuth

    users.get_auth_by_email.return_value = UserAuth(user=existing_user, password_hash="hash")

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.return_value = uuid4()
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="teacher@example.com",
                password="password123",
                first_name="Ada",
                last_name="Lovelace",
            )
        )

    assert exc_info.value.code == ErrorCode.DUPLICATE_ENTRY
    users.create.assert_not_awaited()
    profiles.create.assert_not_awaited()
    verification_tokens.create.assert_not_awaited()
    email_sender.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_user_handles_email_failure_gracefully(now: datetime) -> None:
    """Registration should succeed even if email sending fails."""
    settings = Settings()
    user_id = uuid4()
    token_id = uuid4()
    created_user = make_user(email="teacher@example.com", user_id=user_id).model_copy(
        update={"created_at": now, "updated_at": now, "email_verified": False}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None
    users.create.return_value = created_user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    expected_profile = UserProfile(
        user_id=user_id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    profiles.create.return_value = expected_profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)

    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_sender.send.side_effect = Exception("SMTP connection failed")

    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [user_id, token_id]

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "verification-token"

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    result = await handler.handle(
        RegisterUserCommand(
            email="teacher@example.com",
            password="password123",
            first_name="Ada",
            last_name="Lovelace",
        )
    )

    assert result.user == created_user
    assert result.profile == expected_profile
    assert result.verification_email_sent is False  # Email failed but user was created
    users.create.assert_awaited_once()
    profiles.create.assert_awaited_once()
    verification_tokens.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_user_rejects_empty_first_name(now: datetime) -> None:
    """Registration should fail if first name is empty."""
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="teacher@example.com",
                password="password123",
                first_name="   ",  # Empty after strip
                last_name="Lovelace",
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.get_auth_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_user_rejects_empty_last_name(now: datetime) -> None:
    """Registration should fail if last name is empty."""
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="teacher@example.com",
                password="password123",
                first_name="Ada",
                last_name="",  # Empty
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.get_auth_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_user_rejects_name_too_long(now: datetime) -> None:
    """Registration should fail if name exceeds 100 characters."""
    settings = Settings()

    uow = AsyncMock(spec=UnitOfWorkProtocol)
    uow.__aenter__.return_value = uow
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)

    password_hasher = Mock(spec=PasswordHasherProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    token_generator = Mock(spec=TokenGeneratorProtocol)

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            RegisterUserCommand(
                email="teacher@example.com",
                password="password123",
                first_name="A" * 101,  # Too long
                last_name="Lovelace",
            )
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    users.get_auth_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_user_enters_uow_before_user_creation(now: datetime) -> None:
    """Registration should enter UoW before creating user."""
    events: list[str] = []
    settings = Settings()
    user_id = uuid4()
    created_user = make_user(email="teacher@example.com", user_id=user_id).model_copy(
        update={"created_at": now, "updated_at": now, "email_verified": False}
    )

    uow = AsyncMock(spec=UnitOfWorkProtocol)

    async def enter():
        events.append("uow_enter")
        return uow

    uow.__aenter__.side_effect = enter
    uow.__aexit__.return_value = None

    users = AsyncMock(spec=UserRepositoryProtocol)

    async def get_auth_by_email(_email: str):
        events.append("get_auth_by_email")
        return None

    users.get_auth_by_email.side_effect = get_auth_by_email

    async def create_user(*, user, password_hash):
        _ = (user, password_hash)  # Mark as used
        events.append("create_user")
        return created_user

    users.create.side_effect = create_user

    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    expected_profile = UserProfile(
        user_id=user_id,
        first_name="Ada",
        last_name="Lovelace",
        display_name=None,
        locale="sv-SE",
        created_at=now,
        updated_at=now,
    )
    profiles.create.return_value = expected_profile

    verification_tokens = AsyncMock(spec=EmailVerificationTokenRepositoryProtocol)
    email_sender = AsyncMock(spec=EmailSenderProtocol)
    email_renderer = Mock(spec=EmailTemplateRendererProtocol)
    email_renderer.render.return_value = EmailMessage(
        to_email="teacher@example.com",
        subject="Verifiera din e-postadress",
        html_body="<html>verification link</html>",
        text_body="verification link",
    )

    password_hasher = Mock(spec=PasswordHasherProtocol)
    password_hasher.hash.return_value = "hash"

    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    id_generator = Mock(spec=IdGeneratorProtocol)
    id_generator.new_uuid.side_effect = [user_id, uuid4()]

    token_generator = Mock(spec=TokenGeneratorProtocol)
    token_generator.new_token.return_value = "verification-token"

    handler = RegisterUserHandler(
        settings=settings,
        uow=uow,
        users=users,
        profiles=profiles,
        verification_tokens=verification_tokens,
        email_sender=email_sender,
        email_renderer=email_renderer,
        password_hasher=password_hasher,
        clock=clock,
        id_generator=id_generator,
        token_generator=token_generator,
    )

    await handler.handle(
        RegisterUserCommand(
            email="teacher@example.com",
            password="password123",
            first_name="Ada",
            last_name="Lovelace",
        )
    )

    assert events[0] == "uow_enter"
    assert "get_auth_by_email" in events
    assert "create_user" in events
