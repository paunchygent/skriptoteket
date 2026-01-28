from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Literal, Sequence

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ClpBand

RiskLevel = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True, slots=True)
class RiskLevelBand:
    level: RiskLevel
    min_score: int
    max_score: int


@dataclass(frozen=True, slots=True)
class RiskTemplate:
    id: str
    title: str
    hazard_codes_any: tuple[str, ...]
    default_severity: int
    default_likelihood: int
    measures: tuple[str, ...] = ()
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RiskTemplates:
    risk_levels: tuple[RiskLevelBand, ...]
    hazard_risks: tuple[RiskTemplate, ...]
    generic_risks: tuple[RiskTemplate, ...]


DEFAULT_RISK_LEVELS: tuple[RiskLevelBand, ...] = (
    RiskLevelBand(level="low", min_score=1, max_score=4),
    RiskLevelBand(level="medium", min_score=5, max_score=9),
    RiskLevelBand(level="high", min_score=10, max_score=16),
    RiskLevelBand(level="critical", min_score=17, max_score=25),
)


def score_risk(*, severity: int, likelihood: int) -> int:
    return severity * likelihood


def resolve_risk_level(*, score: int, levels: Sequence[RiskLevelBand]) -> RiskLevel:
    for level in levels:
        if level.min_score <= score <= level.max_score:
            return level.level
    return levels[-1].level if levels else "low"


def select_clp_band(*, bands: Sequence[ClpBand], molarity: Decimal) -> ClpBand | None:
    for band in bands:
        if band.min_molarity is not None and molarity < band.min_molarity:
            continue
        if band.max_molarity is not None and molarity > band.max_molarity:
            continue
        return band
    return None


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
