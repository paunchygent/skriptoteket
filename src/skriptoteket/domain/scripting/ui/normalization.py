from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.scripting.ui.contract_v2 import UiPayloadV2
from skriptoteket.domain.scripting.ui.state_update import NoChangeStateUpdate, StateUpdate


class UiNormalizationResult(BaseModel):
    """Deterministic normalization output used for persistence (ADR-0024)."""

    model_config = ConfigDict(frozen=True)

    ui_payload: UiPayloadV2
    state_update: StateUpdate = Field(default_factory=NoChangeStateUpdate)
