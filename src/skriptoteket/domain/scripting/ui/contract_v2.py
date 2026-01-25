from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator

from skriptoteket.domain.scripting.artifacts import RunnerArtifact


class UiOutputKind(StrEnum):
    NOTICE = "notice"
    MARKDOWN = "markdown"
    TABLE = "table"
    JSON = "json"
    HTML_SANDBOXED = "html_sandboxed"
    VEGA_LITE = "vega_lite"


class UiNoticeLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class UiNoticeOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.NOTICE] = UiOutputKind.NOTICE
    level: UiNoticeLevel
    message: str

    @field_validator("message")
    @classmethod
    def _validate_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("message is required")
        return normalized


class UiMarkdownOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.MARKDOWN] = UiOutputKind.MARKDOWN
    markdown: str

    @field_validator("markdown")
    @classmethod
    def _validate_markdown(cls, value: str) -> str:
        if not value:
            raise ValueError("markdown is required")
        return value


class UiTableColumn(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    label: str

    @field_validator("key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("key is required")
        return normalized

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label is required")
        return normalized


UiTableCellValue = str | int | float | bool | None
UiTableRow = dict[str, UiTableCellValue]


class UiTableOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.TABLE] = UiOutputKind.TABLE
    title: str | None = None
    columns: list[UiTableColumn]
    rows: list[UiTableRow]

    @field_validator("columns")
    @classmethod
    def _validate_columns(cls, value: list[UiTableColumn]) -> list[UiTableColumn]:
        if not value:
            raise ValueError("columns is required")
        keys = [col.key for col in value]
        if len(set(keys)) != len(keys):
            raise ValueError("columns must have unique keys")
        return value

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None


class UiJsonOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.JSON] = UiOutputKind.JSON
    title: str | None = None
    value: JsonValue

    @field_validator("title")
    @classmethod
    def _validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None


class UiHtmlSandboxedOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.HTML_SANDBOXED] = UiOutputKind.HTML_SANDBOXED
    html: str

    @field_validator("html")
    @classmethod
    def _validate_html(cls, value: str) -> str:
        if not value:
            raise ValueError("html is required")
        return value


class UiVegaLiteOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal[UiOutputKind.VEGA_LITE] = UiOutputKind.VEGA_LITE
    spec: JsonValue

    @field_validator("spec")
    @classmethod
    def _validate_spec(cls, value: JsonValue) -> JsonValue:
        if not isinstance(value, dict):
            raise ValueError("spec must be a JSON object")
        return value


UiOutput = Annotated[
    UiNoticeOutput
    | UiMarkdownOutput
    | UiTableOutput
    | UiJsonOutput
    | UiHtmlSandboxedOutput
    | UiVegaLiteOutput,
    Field(discriminator="kind"),
]


class UiActionFieldKind(StrEnum):
    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    MULTI_ENUM = "multi_enum"
    FILE_REF = "file_ref"


class UiFileRefSource(StrEnum):
    SESSION = "session"
    VAULT = "vault"


class UiEnumOption(BaseModel):
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


class UiActionFieldBase(BaseModel):
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


class UiStringField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.STRING] = UiActionFieldKind.STRING


class UiTextField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.TEXT] = UiActionFieldKind.TEXT


class UiIntegerField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.INTEGER] = UiActionFieldKind.INTEGER


class UiNumberField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.NUMBER] = UiActionFieldKind.NUMBER


class UiBooleanField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.BOOLEAN] = UiActionFieldKind.BOOLEAN


class UiEnumField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.ENUM] = UiActionFieldKind.ENUM
    options: list[UiEnumOption]

    @field_validator("options")
    @classmethod
    def _validate_options(cls, value: list[UiEnumOption]) -> list[UiEnumOption]:
        if not value:
            raise ValueError("options is required")
        return value


class UiMultiEnumField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.MULTI_ENUM] = UiActionFieldKind.MULTI_ENUM
    options: list[UiEnumOption]

    @field_validator("options")
    @classmethod
    def _validate_options(cls, value: list[UiEnumOption]) -> list[UiEnumOption]:
        if not value:
            raise ValueError("options is required")
        return value


class UiFileRefField(UiActionFieldBase):
    kind: Literal[UiActionFieldKind.FILE_REF] = UiActionFieldKind.FILE_REF

    min: int
    max: int
    sources: list[UiFileRefSource] | None = None

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

    @field_validator("sources")
    @classmethod
    def _normalize_sources(
        cls, value: list[UiFileRefSource] | None
    ) -> list[UiFileRefSource] | None:
        if value is None:
            return None
        normalized: list[UiFileRefSource] = []
        seen: set[UiFileRefSource] = set()
        for item in value:
            if item in seen:
                continue
            normalized.append(item)
            seen.add(item)
        return normalized or None

    @model_validator(mode="after")
    def _validate_range(self) -> UiFileRefField:
        if self.max < self.min:
            raise ValueError("max must be >= min")
        return self


UiActionField = Annotated[
    UiStringField
    | UiTextField
    | UiIntegerField
    | UiNumberField
    | UiBooleanField
    | UiEnumField
    | UiMultiEnumField
    | UiFileRefField,
    Field(discriminator="kind"),
]


class UiFormAction(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_id: str
    label: str
    kind: Literal["form"] = "form"
    fields: list[UiActionField] = Field(default_factory=list)
    prefill: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("action_id")
    @classmethod
    def _validate_action_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("action_id is required")
        return normalized

    @field_validator("label")
    @classmethod
    def _validate_label(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("label is required")
        return normalized


class ToolUiContractV2Result(BaseModel):
    """Raw contract v2 payload (runner-based tools or curated apps)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal[2] = 2
    status: Literal["succeeded", "failed", "timed_out"]
    error_summary: str | None
    outputs: list[UiOutput] = Field(default_factory=list)
    next_actions: list[UiFormAction] = Field(default_factory=list)
    state: dict[str, JsonValue] | None = None
    artifacts: list[RunnerArtifact] = Field(default_factory=list)

    @field_validator("state")
    @classmethod
    def _validate_state(cls, value: dict[str, JsonValue] | None) -> dict[str, JsonValue] | None:
        if value is None:
            return None
        for key in value:
            if not key.strip():
                raise ValueError("state keys must be non-empty strings")
        return value


class UiPayloadV2(BaseModel):
    """Stored UI payload (rendering source of truth; ADR-0024)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal[2] = 2
    outputs: list[UiOutput] = Field(default_factory=list)
    next_actions: list[UiFormAction] = Field(default_factory=list)
