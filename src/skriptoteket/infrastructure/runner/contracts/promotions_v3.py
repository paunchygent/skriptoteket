from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.file_refs import parse_file_ref
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.infrastructure.runner.path_safety import validate_output_path


class PromotionRequestV3(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    kind: Literal["session"]
    source_path: str
    name: str
    ref: str | None = None

    @field_validator("request_id")
    @classmethod
    def _validate_request_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("request_id is required")
        return normalized

    @field_validator("source_path")
    @classmethod
    def _validate_source_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source_path is required")
        try:
            validate_output_path(path=normalized)
        except DomainError as exc:
            raise ValueError(exc.message) from exc
        return normalized

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        try:
            return sanitize_input_filename(input_filename=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc

    @field_validator("ref")
    @classmethod
    def _validate_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parse_file_ref(value=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc
        return value


class PromotionResultV3(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    status: Literal["applied", "rejected"]
    ref: str | None = None
    reason: str | None = None

    @field_validator("request_id")
    @classmethod
    def _validate_request_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("request_id is required")
        return normalized

    @field_validator("ref")
    @classmethod
    def _validate_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parse_file_ref(value=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc
        return value


class PromotionEnvelopeV3(BaseModel):
    model_config = ConfigDict(frozen=True)

    requests: list[PromotionRequestV3]
    results: list[PromotionResultV3]


def validate_promotion_envelope(*, promotions: PromotionEnvelopeV3) -> None:
    request_ids = [request.request_id for request in promotions.requests]
    unique_ids = set(request_ids)
    if len(unique_ids) != len(request_ids):
        raise DomainError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Runner contract violation: duplicate promotion request ids",
            details={"request_ids": request_ids},
        )

    for result in promotions.results:
        if result.request_id not in unique_ids:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Runner contract violation: promotion result without request",
                details={"request_id": result.request_id},
            )
