from __future__ import annotations

from skriptoteket.domain.errors import ErrorCode

ERROR_CODE_TO_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.ACCOUNT_LOCKED: 423,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.SESSION_NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.DUPLICATE_ENTRY: 409,
    ErrorCode.EMAIL_SEND_FAILED: 503,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
}


def error_to_status(code: ErrorCode) -> int:
    return ERROR_CODE_TO_STATUS.get(code, 500)
