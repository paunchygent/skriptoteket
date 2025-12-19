from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator

from skriptoteket.domain.scripting.ui.contract_v2 import UiActionFieldKind, UiOutputKind


class UiPolicyProfileId(StrEnum):
    DEFAULT = "default"
    CURATED = "curated"


class UiPolicyBudgets(BaseModel):
    model_config = ConfigDict(frozen=True)

    state_max_bytes: int
    ui_payload_max_bytes: int

    @field_validator("state_max_bytes", "ui_payload_max_bytes")
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must be >= 0")
        return value


class UiPolicyCaps(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_outputs: int
    max_next_actions: int
    max_fields_per_action: int

    markdown_max_bytes: int
    html_sandboxed_max_bytes: int

    table_max_rows: int
    table_max_cols: int
    table_cell_max_bytes: int

    json_max_bytes: int
    json_max_depth: int
    json_max_keys: int
    json_max_array_len: int

    vega_lite_spec_max_bytes: int

    enum_max_options: int
    multi_enum_max_options: int

    @field_validator(
        "max_outputs",
        "max_next_actions",
        "max_fields_per_action",
        "markdown_max_bytes",
        "html_sandboxed_max_bytes",
        "table_max_rows",
        "table_max_cols",
        "table_cell_max_bytes",
        "json_max_bytes",
        "json_max_depth",
        "json_max_keys",
        "json_max_array_len",
        "vega_lite_spec_max_bytes",
        "enum_max_options",
        "multi_enum_max_options",
    )
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must be >= 0")
        return value


class UiPolicy(BaseModel):
    """Policy profile for allowlists + size budgets used by the normalizer (ADR-0024)."""

    model_config = ConfigDict(frozen=True)

    profile_id: UiPolicyProfileId
    allowed_output_kinds: frozenset[UiOutputKind]
    allowed_action_field_kinds: frozenset[UiActionFieldKind]
    budgets: UiPolicyBudgets
    caps: UiPolicyCaps

    @field_validator("allowed_output_kinds", "allowed_action_field_kinds")
    @classmethod
    def _validate_non_empty_set(cls, value: frozenset[object]) -> frozenset[object]:
        if not value:
            raise ValueError("set must be non-empty")
        return value


_KIB = 1024

DEFAULT_UI_POLICY = UiPolicy(
    profile_id=UiPolicyProfileId.DEFAULT,
    allowed_output_kinds=frozenset(
        {
            UiOutputKind.NOTICE,
            UiOutputKind.MARKDOWN,
            UiOutputKind.TABLE,
            UiOutputKind.JSON,
            UiOutputKind.HTML_SANDBOXED,
        }
    ),
    allowed_action_field_kinds=frozenset(
        {
            UiActionFieldKind.STRING,
            UiActionFieldKind.TEXT,
            UiActionFieldKind.INTEGER,
            UiActionFieldKind.NUMBER,
            UiActionFieldKind.BOOLEAN,
            UiActionFieldKind.ENUM,
            UiActionFieldKind.MULTI_ENUM,
        }
    ),
    budgets=UiPolicyBudgets(
        state_max_bytes=64 * _KIB,
        ui_payload_max_bytes=256 * _KIB,
    ),
    caps=UiPolicyCaps(
        max_outputs=50,
        max_next_actions=10,
        max_fields_per_action=25,
        markdown_max_bytes=64 * _KIB,
        html_sandboxed_max_bytes=96 * _KIB,
        table_max_rows=750,
        table_max_cols=40,
        table_cell_max_bytes=512,
        json_max_bytes=96 * _KIB,
        json_max_depth=10,
        json_max_keys=1_000,
        json_max_array_len=2_000,
        vega_lite_spec_max_bytes=0,
        enum_max_options=100,
        multi_enum_max_options=200,
    ),
)

CURATED_UI_POLICY = UiPolicy(
    profile_id=UiPolicyProfileId.CURATED,
    allowed_output_kinds=frozenset(
        {
            UiOutputKind.NOTICE,
            UiOutputKind.MARKDOWN,
            UiOutputKind.TABLE,
            UiOutputKind.JSON,
            UiOutputKind.HTML_SANDBOXED,
            UiOutputKind.VEGA_LITE,
        }
    ),
    allowed_action_field_kinds=DEFAULT_UI_POLICY.allowed_action_field_kinds,
    budgets=UiPolicyBudgets(
        state_max_bytes=256 * _KIB,
        ui_payload_max_bytes=512 * _KIB,
    ),
    caps=UiPolicyCaps(
        max_outputs=150,
        max_next_actions=25,
        max_fields_per_action=60,
        markdown_max_bytes=256 * _KIB,
        html_sandboxed_max_bytes=192 * _KIB,
        table_max_rows=2_500,
        table_max_cols=80,
        table_cell_max_bytes=1_024,
        json_max_bytes=256 * _KIB,
        json_max_depth=20,
        json_max_keys=5_000,
        json_max_array_len=10_000,
        vega_lite_spec_max_bytes=256 * _KIB,
        enum_max_options=300,
        multi_enum_max_options=600,
    ),
)


def get_ui_policy(*, profile_id: UiPolicyProfileId) -> UiPolicy:
    if profile_id is UiPolicyProfileId.DEFAULT:
        return DEFAULT_UI_POLICY
    if profile_id is UiPolicyProfileId.CURATED:
        return CURATED_UI_POLICY
    raise ValueError(f"Unknown UiPolicyProfileId: {profile_id}")
