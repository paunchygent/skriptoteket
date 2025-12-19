from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2


class UiNormalizationResult(BaseModel):
    """Deterministic normalization output used for persistence (ADR-0024)."""

    model_config = ConfigDict(frozen=True)

    ui_payload: UiPayloadV2
    state: dict[str, JsonValue] = Field(default_factory=dict)

