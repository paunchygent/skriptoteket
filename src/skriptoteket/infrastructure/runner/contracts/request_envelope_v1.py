from __future__ import annotations

import json
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.input_files import sanitize_input_filename

from .file_refs import parse_file_ref

_INPUT_ROOT = PurePosixPath("/work/input")


class RunnerRequestInputs(BaseModel):
    model_config = ConfigDict(frozen=True)

    values: dict[str, JsonValue] = Field(default_factory=dict)


class RunnerRequestAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    input: dict[str, JsonValue]
    state: dict[str, JsonValue]

    @field_validator("action_id")
    @classmethod
    def _validate_action_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("action_id is required")
        return normalized


class RunnerRequestFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    path: str
    bytes: int
    ref: str | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        try:
            return sanitize_input_filename(input_filename=value)
        except DomainError as exc:
            raise ValueError(exc.message) from exc

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("path is required")
        path = PurePosixPath(normalized)
        if not path.is_absolute():
            raise ValueError("path must be absolute")
        if ".." in path.parts:
            raise ValueError("path must not contain traversal")
        if path.parts[: len(_INPUT_ROOT.parts)] != _INPUT_ROOT.parts:
            raise ValueError("path must be under /work/input")
        return normalized

    @field_validator("bytes")
    @classmethod
    def _validate_bytes(cls, value: int) -> int:
        if value < 0:
            raise ValueError("bytes must be >= 0")
        return value

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


class RunnerRequestEnvelopeV1(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = Field(default=1, frozen=True)
    inputs: RunnerRequestInputs
    action: RunnerRequestAction | None = None
    files: list[RunnerRequestFile] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def _validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError("schema_version must be 1")
        return value


def render_request_envelope_json(*, payload: RunnerRequestEnvelopeV1) -> bytes:
    data = payload.model_dump(mode="json", exclude_none=True)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
