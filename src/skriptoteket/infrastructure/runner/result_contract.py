from __future__ import annotations

import json
from typing import TypeGuard

from pydantic import ValidationError

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.ui.contract_v2 import ToolUiContractV2Result
from skriptoteket.infrastructure.runner.path_safety import validate_output_path


def _is_object(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict)


def parse_runner_result_json(*, result_json_bytes: bytes) -> ToolUiContractV2Result:
    try:
        raw = json.loads(result_json_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json",
        ) from exc

    if not _is_object(raw):
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json schema",
        )

    contract_version = raw.get("contract_version")
    if contract_version != 2:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: unsupported contract_version",
            details={"contract_version": contract_version},
        )

    try:
        payload = ToolUiContractV2Result.model_validate(raw)
    except ValidationError as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json schema",
            details={"errors": exc.errors()},
        ) from exc

    for artifact in payload.artifacts:
        validate_output_path(path=artifact.path)

    return payload
