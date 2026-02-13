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
    matches: list[ClpBand] = []
    for band in bands:
        if band.min_molarity is not None and molarity < band.min_molarity:
            continue
        if band.max_molarity is not None and molarity > band.max_molarity:
            continue
        matches.append(band)
    if not matches:
        return None

    hazard_codes: list[str] = []
    pictograms: list[str] = []
    notes: list[str] = []
    hazard_seen: set[str] = set()
    pictogram_seen: set[str] = set()
    notes_seen: set[str] = set()
    has_danger = False
    has_warning = False

    for band in matches:
        for code in band.hazard_codes:
            if code in hazard_seen:
                continue
            hazard_seen.add(code)
            hazard_codes.append(code)
        for pictogram in band.pictograms:
            if pictogram in pictogram_seen:
                continue
            pictogram_seen.add(pictogram)
            pictograms.append(pictogram)
        for note in band.notes:
            if note in notes_seen:
                continue
            notes_seen.add(note)
            notes.append(note)
        if band.signal_word == "danger":
            has_danger = True
        if band.signal_word == "warning":
            has_warning = True

    min_bounds = [band.min_molarity for band in matches if band.min_molarity is not None]
    max_bounds = [band.max_molarity for band in matches if band.max_molarity is not None]
    min_molarity = max(min_bounds) if min_bounds else None
    max_molarity = min(max_bounds) if max_bounds else None
    signal_word: Literal["danger", "warning"] | None
    if has_danger:
        signal_word = "danger"
    elif has_warning:
        signal_word = "warning"
    else:
        signal_word = None

    return ClpBand(
        min_molarity=min_molarity,
        max_molarity=max_molarity,
        hazard_codes=tuple(hazard_codes),
        pictograms=tuple(pictograms),
        signal_word=signal_word,
        notes=tuple(notes),
    )


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
