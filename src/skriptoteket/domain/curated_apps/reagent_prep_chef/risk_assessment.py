from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class RiskTemplate:
    id: str
    title: str
    hazard_codes_any: tuple[str, ...] = ()
    measures: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RiskTemplates:
    hazard_risks: tuple[RiskTemplate, ...]
    generic_risks: tuple[RiskTemplate, ...]


def filter_templates_by_hazard_codes(
    *, templates: Iterable[RiskTemplate], hazard_codes: set[str]
) -> list[RiskTemplate]:
    matched: list[RiskTemplate] = []
    for template in templates:
        if not template.hazard_codes_any:
            continue
        if hazard_codes.intersection(template.hazard_codes_any):
            matched.append(template)
    return matched
