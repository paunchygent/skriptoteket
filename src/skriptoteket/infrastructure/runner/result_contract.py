from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import RunnerArtifact
from skriptoteket.infrastructure.runner.path_safety import validate_output_path


class RunnerResultPayload(BaseModel):
    contract_version: int
    status: Literal["succeeded", "failed", "timed_out"]
    html_output: str
    error_summary: str | None
    artifacts: list[RunnerArtifact] = Field(default_factory=list)


def parse_runner_result_json(*, result_json_bytes: bytes) -> RunnerResultPayload:
    try:
        raw = json.loads(result_json_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json",
        ) from exc

    try:
        payload = RunnerResultPayload.model_validate(raw)
    except ValidationError as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json schema",
            details={"errors": exc.errors()},
        ) from exc

    if payload.contract_version != 1:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: unsupported contract_version",
            details={"contract_version": payload.contract_version},
        )

    for artifact in payload.artifacts:
        validate_output_path(path=artifact.path)

    return payload
