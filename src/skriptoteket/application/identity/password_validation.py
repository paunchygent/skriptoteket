from __future__ import annotations

from skriptoteket.domain.errors import DomainError, ErrorCode

MIN_PASSWORD_LENGTH = 8


def validate_password_strength(*, password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Lösenordet måste vara minst {MIN_PASSWORD_LENGTH} tecken",
            details={"min_length": MIN_PASSWORD_LENGTH},
        )
