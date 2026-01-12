from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.scripting.tool_inputs import ToolInputField
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField


class ScriptBankSeedGroup(StrEnum):
    CURATED = "curated"
    TEST = "test"


class ScriptBankEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    summary: str | None = None
    usage_instructions: str | None = None
    profession_slugs: list[str]
    category_slugs: list[str]
    seed_group: ScriptBankSeedGroup = ScriptBankSeedGroup.CURATED
    entrypoint: str = "run_tool"
    source_filename: str
    settings_schema: list[UiActionField] | None = None
    input_schema: list[ToolInputField] = Field(default_factory=list)
