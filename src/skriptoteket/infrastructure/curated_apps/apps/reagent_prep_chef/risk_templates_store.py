from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from skriptoteket.domain.curated_apps.reagent_prep_chef.risk_assessment import (
    RiskTemplate,
    RiskTemplates,
)
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefRiskTemplateStoreProtocol


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("expected string")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("required text value is empty")
    return cleaned


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("expected string")
    cleaned = value.strip()
    return cleaned or None


def _clean_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected list")
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise ValueError("expected list of strings")
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
    return cleaned


class _RiskTemplateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    hazard_codes_any: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    description: str | None = None

    _strip_id = field_validator("id", mode="before")(_clean_text)
    _strip_title = field_validator("title", mode="before")(_clean_text)
    _strip_hazard_codes_any = field_validator("hazard_codes_any", mode="before")(_clean_text_list)
    _strip_measures = field_validator("measures", mode="before")(_clean_text_list)
    _strip_description = field_validator("description", mode="before")(_clean_optional_text)


class _RiskTemplatesModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int | None = None
    risk_items: list[_RiskTemplateModel] = Field(default_factory=list)
    generic_risks: list[_RiskTemplateModel] = Field(default_factory=list)


_TEMPLATES_ADAPTER = TypeAdapter(_RiskTemplatesModel)


class InMemoryReagentPrepChefRiskTemplateStore(ReagentPrepChefRiskTemplateStoreProtocol):
    def __init__(self, *, templates_path: Path) -> None:
        self._templates = _load_templates(templates_path)

    def get(self) -> RiskTemplates:
        return self._templates


def _load_templates(path: Path) -> RiskTemplates:
    payload = path.read_text(encoding="utf-8")
    parsed = _TEMPLATES_ADAPTER.validate_json(payload)

    hazard_items = tuple(_to_template(item) for item in parsed.risk_items)
    generic_items = tuple(_to_template(item) for item in parsed.generic_risks)

    return RiskTemplates(
        hazard_risks=hazard_items,
        generic_risks=generic_items,
    )


def _to_template(model: _RiskTemplateModel) -> RiskTemplate:
    return RiskTemplate(
        id=model.id,
        title=model.title,
        hazard_codes_any=tuple(model.hazard_codes_any),
        measures=tuple(model.measures),
        description=model.description,
    )
