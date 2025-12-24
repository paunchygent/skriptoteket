from __future__ import annotations

import re

from skriptoteket.domain.errors import DomainError, ErrorCode

EMAIL_MAX_LENGTH = 255

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(*, email: str) -> str:
    normalized = normalize_email(email)

    if not normalized:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="E-postadress måste anges",
        )

    if len(normalized) > EMAIL_MAX_LENGTH:
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="E-postadress är för lång",
        )

    if not _EMAIL_RE.match(normalized):
        raise DomainError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Ogiltig e-postadress",
        )

    return normalized
