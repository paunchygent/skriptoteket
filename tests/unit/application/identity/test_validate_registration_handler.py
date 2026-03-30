"""Unit tests for anonymous registration preflight validation.

Purpose:
    Verify that the public register form gets field-level feedback from the
    backend without mutating any persisted user state.

Relationships:
    - Exercises `ValidateRegistrationHandler` directly.
    - Reuses the shared identity protocols that the SPA-facing auth route binds.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.identity.commands import ValidateRegistrationCommand
from skriptoteket.application.identity.handlers.validate_registration_input import (
    ValidateRegistrationHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import UserAuth
from skriptoteket.protocols.identity import DomainValidatorProtocol, UserRepositoryProtocol
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.asyncio
async def test_validate_registration_returns_incomplete_for_blank_fields() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    domain_validator = Mock(spec=DomainValidatorProtocol)
    handler = ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

    result = await handler.handle(ValidateRegistrationCommand(email="", password=""))

    assert result.email.status == "incomplete"
    assert result.email.message is None
    assert result.password.status == "incomplete"
    assert result.password.message is None
    users.get_auth_by_email.assert_not_awaited()
    domain_validator.validate_registration_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_registration_maps_invalid_email_format() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    domain_validator = Mock(spec=DomainValidatorProtocol)
    domain_validator.extract_root_domain_from_email.side_effect = DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message="Ogiltig e-postadress",
    )
    handler = ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

    result = await handler.handle(
        ValidateRegistrationCommand(email="not-an-email", password="password123")
    )

    assert result.email.status == "invalid"
    assert result.email.message == "Ange en giltig e-postadress."
    assert result.password.status == "valid"
    users.get_auth_by_email.assert_not_awaited()
    domain_validator.validate_registration_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_registration_rejects_duplicate_email_before_allowlist_check() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = UserAuth(
        user=make_user(email="teacher@example.com"),
        password_hash="hash",
    )
    domain_validator = Mock(spec=DomainValidatorProtocol)
    handler = ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

    result = await handler.handle(
        ValidateRegistrationCommand(email="teacher@example.com", password="password123")
    )

    assert result.email.status == "invalid"
    assert result.email.message == "E-postadressen är redan registrerad."
    domain_validator.validate_registration_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_registration_maps_disallowed_domain_to_helpful_message() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_auth_by_email.return_value = None
    domain_validator = Mock(spec=DomainValidatorProtocol)
    domain_validator.validate_registration_email.side_effect = DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message="E-postdomänen är inte godkänd för registrering",
    )
    handler = ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

    result = await handler.handle(
        ValidateRegistrationCommand(email="teacher@gmail.com", password="password123")
    )

    assert result.email.status == "invalid"
    assert result.email.message == (
        "Endast kommuner och enskilda huvudmän kan registrera sig just nu. "
        "Använd din tjänsteadress från kommunen eller huvudmannen."
    )


@pytest.mark.asyncio
async def test_validate_registration_reuses_password_policy_messages() -> None:
    users = AsyncMock(spec=UserRepositoryProtocol)
    domain_validator = Mock(spec=DomainValidatorProtocol)
    handler = ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

    result = await handler.handle(
        ValidateRegistrationCommand(email="teacher@example.com", password="short")
    )

    assert result.password.status == "invalid"
    assert result.password.message == "Lösenordet måste vara minst 8 tecken"
