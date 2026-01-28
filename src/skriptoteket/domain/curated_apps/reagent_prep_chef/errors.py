from __future__ import annotations

from enum import StrEnum

from skriptoteket.domain.errors import DomainError, ErrorCode, ErrorDetails


class ReagentPrepChefErrorCode(StrEnum):
    INVALID_FORMULA = "ERR_INVALID_FORMULA"
    STOCK_MISSING = "ERR_STOCK_MISSING"
    IMPOSSIBLE_DILUTION = "ERR_IMPOSSIBLE_DILUTION"
    RISK_CONFIRMATION_REQUIRED = "ERR_RISK_CONFIRMATION_REQUIRED"
    RISK_CONTEXT_INCOMPLETE = "ERR_RISK_CONTEXT_INCOMPLETE"
    RISK_CHEMICAL_MISSING = "ERR_RISK_CHEMICAL_MISSING"
    RISK_SDS_MISSING = "ERR_RISK_SDS_MISSING"


def rpc_validation_error(
    *,
    app_code: ReagentPrepChefErrorCode,
    message: str,
    details: ErrorDetails | None = None,
) -> DomainError:
    payload: ErrorDetails = {"app_error_code": app_code.value}
    if details:
        payload.update(details)
    return DomainError(code=ErrorCode.VALIDATION_ERROR, message=message, details=payload)
