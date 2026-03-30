"""Anonymous registration preflight validation handler.

Purpose:
  Provide a lightweight, structured validation result for the SPA register form
  so email-domain, duplicate-email, and password-policy feedback can be shown
  before submit without duplicating the backend rules in the browser.

Relationships:
  - Reuses `TldextractDomainValidator` through `DomainValidatorProtocol`.
  - Reuses the shared password policy from `password_validation.py`.
  - Reads existing users through `UserRepositoryProtocol` for duplicate-email
    feedback while leaving final registration authority to `RegisterUserHandler`.
"""

from __future__ import annotations

from skriptoteket.application.identity.commands import (
    RegistrationValidationField,
    ValidateRegistrationCommand,
    ValidateRegistrationResult,
)
from skriptoteket.application.identity.password_validation import validate_password_strength
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.identity import (
    DomainValidatorProtocol,
    UserRepositoryProtocol,
    ValidateRegistrationHandlerProtocol,
)

_REGISTRATION_DOMAIN_MESSAGE = (
    "Endast anställda hos kommuner och enskilda huvudmän kan registrera sig just nu. "
    "Använd din e-postadress från kommun eller enskild huvudman."
)


def _field(*, status: str, message: str | None = None) -> RegistrationValidationField:
    return RegistrationValidationField(status=status, message=message)


class ValidateRegistrationHandler(ValidateRegistrationHandlerProtocol):
    """Validate email/password inputs for the public register form."""

    def __init__(
        self,
        *,
        users: UserRepositoryProtocol,
        domain_validator: DomainValidatorProtocol,
    ) -> None:
        self._users = users
        self._domain_validator = domain_validator

    async def handle(self, command: ValidateRegistrationCommand) -> ValidateRegistrationResult:
        return ValidateRegistrationResult(
            email=await self._validate_email(command.email),
            password=self._validate_password(command.password),
        )

    async def _validate_email(self, email: str | None) -> RegistrationValidationField:
        candidate = (email or "").strip()
        if candidate == "":
            return _field(status="incomplete")

        try:
            self._domain_validator.extract_root_domain_from_email(candidate)
        except DomainError as exc:
            return self._invalid_email_field(exc)

        existing_user = await self._users.get_auth_by_email(candidate)
        if existing_user is not None:
            return _field(status="invalid", message="E-postadressen är redan registrerad.")

        try:
            await self._domain_validator.validate_registration_email(candidate)
        except DomainError as exc:
            return self._invalid_email_field(exc)

        return _field(status="valid")

    def _validate_password(self, password: str | None) -> RegistrationValidationField:
        candidate = password or ""
        if candidate == "":
            return _field(status="incomplete")

        try:
            validate_password_strength(password=candidate)
        except DomainError as exc:
            return _field(status="invalid", message=exc.message)

        return _field(status="valid")

    def _invalid_email_field(self, exc: DomainError) -> RegistrationValidationField:
        if exc.code is not ErrorCode.VALIDATION_ERROR:
            return _field(
                status="invalid",
                message="Det gick inte att kontrollera e-postadressen just nu.",
            )

        if exc.message == "Ogiltig e-postadress":
            return _field(status="invalid", message="Ange en giltig e-postadress.")

        if exc.message in {
            "E-postdomänen är inte tillåten för registrering",
            "E-postdomänen är inte godkänd för registrering",
        }:
            return _field(status="invalid", message=_REGISTRATION_DOMAIN_MESSAGE)

        return _field(status="invalid", message=exc.message)
