from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import RunnerArtifact
from skriptoteket.domain.scripting.ui.contract_v2 import UiFormAction, UiOutput
from skriptoteket.infrastructure.runner.path_safety import validate_output_path

from .promotions_v3 import PromotionEnvelopeV3, validate_promotion_envelope
from .state_update_v3 import StateUpdate


class RunnerErrorV3(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["tool_user_error", "tool_runtime_error", "contract_violation"]
    code: str
    details: dict[str, object] | None = None


class RunnerResultPayloadV3(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: Literal[3] = 3
    status: Literal["succeeded", "failed", "timed_out"]
    outputs: list[UiOutput] = Field(default_factory=list)
    next_actions: list[UiFormAction] = Field(default_factory=list)
    state_update: StateUpdate
    error_summary: str | None = None
    error: RunnerErrorV3 | None = None
    artifacts: list[RunnerArtifact] = Field(default_factory=list)
    promotions: PromotionEnvelopeV3 | None = None


def parse_runner_result_v3(*, result_json_bytes: bytes) -> RunnerResultPayloadV3:
    try:
        raw = json.loads(result_json_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json",
        ) from exc

    if not isinstance(raw, dict):
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json schema",
        )

    contract_version = raw.get("contract_version")
    if contract_version != 3:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: unsupported contract_version",
            details={"contract_version": contract_version},
        )

    try:
        payload = RunnerResultPayloadV3.model_validate(raw)
    except ValidationError as exc:
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: invalid result.json schema",
            details={"errors": exc.errors()},
        ) from exc

    for artifact in payload.artifacts:
        validate_output_path(path=artifact.path)

    if payload.promotions is not None:
        validate_promotion_envelope(promotions=payload.promotions)

    return payload
