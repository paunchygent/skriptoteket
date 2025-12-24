from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScriptBankEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    summary: str | None = None
    usage_instructions: str | None = None
    profession_slugs: list[str]
    category_slugs: list[str]
    entrypoint: str = "run_tool"
    source_filename: str
