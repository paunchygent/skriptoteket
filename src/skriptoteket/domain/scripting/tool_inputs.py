from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error


class ToolInputFieldKind(StrEnum):
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    FILE = "file"


class ToolInputEnumOption(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str
    label: str

    @field_validator("value")
    @classmethod
    def _validate_value(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label is required")
        return normalized


class ToolInputFieldBase(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    label: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name is required")
        return normalized

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label is required")
        return normalized


class ToolInputStringField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.STRING] = ToolInputFieldKind.STRING


class ToolInputTextField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.TEXT] = ToolInputFieldKind.TEXT


class ToolInputIntegerField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.INTEGER] = ToolInputFieldKind.INTEGER


class ToolInputNumberField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.NUMBER] = ToolInputFieldKind.NUMBER


class ToolInputBooleanField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.BOOLEAN] = ToolInputFieldKind.BOOLEAN


class ToolInputEnumField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.ENUM] = ToolInputFieldKind.ENUM
    options: list[ToolInputEnumOption]

    @field_validator("options")
    @classmethod
    def _validate_options(cls, value: list[ToolInputEnumOption]) -> list[ToolInputEnumOption]:
        if not value:
            raise ValueError("options is required")
        return value


class ToolInputFileField(ToolInputFieldBase):
    kind: Literal[ToolInputFieldKind.FILE] = ToolInputFieldKind.FILE

    accept: list[str] | None = None
    min: int
    max: int

    @field_validator("accept")
    @classmethod
    def _normalize_accept(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            stripped = item.strip()
            if not stripped:
                continue
            if stripped in seen:
                continue
            normalized.append(stripped)
            seen.add(stripped)
        return normalized or None

    @field_validator("min")
    @classmethod
    def _validate_min(cls, value: int) -> int:
        if value < 0:
            raise ValueError("min must be >= 0")
        return value

    @field_validator("max")
    @classmethod
    def _validate_max(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max must be >= 1")
        return value

    @model_validator(mode="after")
    def _validate_range(self) -> ToolInputFileField:
        if self.max < self.min:
            raise ValueError("max must be >= min")
        return self


ToolInputField = Annotated[
    ToolInputStringField
    | ToolInputTextField
    | ToolInputIntegerField
    | ToolInputNumberField
    | ToolInputBooleanField
    | ToolInputEnumField
    | ToolInputFileField,
    Field(discriminator="kind"),
]

type ToolInputSchema = list[ToolInputField]
type ToolInputValues = dict[str, JsonValue]


def normalize_tool_input_schema(*, input_schema: ToolInputSchema) -> ToolInputSchema:
    seen_names: set[str] = set()
    duplicates: set[str] = set()
    file_field_count = 0

    for field in input_schema:
        if field.name in seen_names:
            duplicates.add(field.name)
        seen_names.add(field.name)

        if field.kind is ToolInputFieldKind.FILE:
            file_field_count += 1

    if duplicates:
        raise validation_error(
            "input_schema contains duplicate field names",
            details={"duplicates": sorted(duplicates)},
        )

    if file_field_count > 1:
        raise validation_error(
            "input_schema can contain at most one file field",
            details={"file_fields": file_field_count},
        )

    return input_schema


def get_file_field(*, input_schema: ToolInputSchema) -> ToolInputFileField | None:
    for field in input_schema:
        if field.kind is not ToolInputFieldKind.FILE:
            continue
        if not isinstance(field, ToolInputFileField):
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Invalid input_schema (file field mismatch)",
                details={"field": field.name, "kind": field.kind.value},
            )
        return field
    return None


def validate_input_files_count(*, input_schema: ToolInputSchema, files_count: int) -> None:
    if files_count < 0:
        raise validation_error("files_count must be >= 0", details={"files_count": files_count})

    file_field = get_file_field(input_schema=input_schema)
    if file_field is None:
        if files_count > 0:
            raise validation_error(
                "Tool does not accept files",
                details={"files_count": files_count},
            )
        return

    if files_count < file_field.min or files_count > file_field.max:
        raise validation_error(
            "Invalid number of uploaded files",
            details={
                "min": file_field.min,
                "max": file_field.max,
                "files_count": files_count,
            },
        )


def normalize_tool_input_values(
    *,
    input_schema: ToolInputSchema,
    values: ToolInputValues,
) -> ToolInputValues:
    by_name = {field.name: field for field in input_schema}
    unknown_keys = sorted([key for key in values.keys() if key not in by_name])
    if unknown_keys:
        raise validation_error(
            "Unknown input keys",
            details={"unknown_keys": unknown_keys},
        )

    normalized: ToolInputValues = {}

    for field in input_schema:
        if field.kind is ToolInputFieldKind.FILE:
            if field.name in values:
                raise validation_error(
                    "File fields are not part of inputs JSON",
                    details={"field": field.name, "kind": field.kind.value},
                )
            continue

        if field.name not in values:
            continue

        raw = values[field.name]
        if raw is None:
            continue

        if field.kind in {ToolInputFieldKind.STRING, ToolInputFieldKind.TEXT}:
            if not isinstance(raw, str):
                raise validation_error(
                    "Invalid input value (expected string)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            stripped = raw.strip()
            if not stripped:
                continue
            normalized[field.name] = stripped
            continue

        if field.kind is ToolInputFieldKind.INTEGER:
            if isinstance(raw, bool):
                raise validation_error(
                    "Invalid input value (expected integer)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            if isinstance(raw, int):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    normalized[field.name] = int(stripped)
                except ValueError as exc:
                    raise validation_error(
                        "Invalid input value (expected integer)",
                        details={"field": field.name, "kind": field.kind.value},
                    ) from exc
                continue
            raise validation_error(
                "Invalid input value (expected integer)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is ToolInputFieldKind.NUMBER:
            if isinstance(raw, bool):
                raise validation_error(
                    "Invalid input value (expected number)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            if isinstance(raw, (int, float)):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    normalized[field.name] = float(stripped)
                except ValueError as exc:
                    raise validation_error(
                        "Invalid input value (expected number)",
                        details={"field": field.name, "kind": field.kind.value},
                    ) from exc
                continue
            raise validation_error(
                "Invalid input value (expected number)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is ToolInputFieldKind.BOOLEAN:
            if isinstance(raw, bool):
                normalized[field.name] = raw
                continue
            if isinstance(raw, str):
                stripped = raw.strip().lower()
                if not stripped:
                    continue
                if stripped in {"true", "1", "yes", "on"}:
                    normalized[field.name] = True
                    continue
                if stripped in {"false", "0", "no", "off"}:
                    normalized[field.name] = False
                    continue
            raise validation_error(
                "Invalid input value (expected boolean)",
                details={"field": field.name, "kind": field.kind.value},
            )

        if field.kind is ToolInputFieldKind.ENUM:
            if not isinstance(raw, str):
                raise validation_error(
                    "Invalid input value (expected enum value)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            stripped = raw.strip()
            if not stripped:
                continue
            if not isinstance(field, ToolInputEnumField):
                raise validation_error(
                    "Invalid input_schema (enum field mismatch)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            options = {opt.value for opt in field.options}
            if stripped not in options:
                raise validation_error(
                    "Invalid input value (unknown enum option)",
                    details={"field": field.name, "kind": field.kind.value},
                )
            normalized[field.name] = stripped
            continue

        raise validation_error(
            "Invalid input_schema (unknown field kind)",
            details={"field": field.name, "kind": field.kind.value},
        )

    return normalized
