from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

type SourceType = Literal["solid", "liquid_stock"]
type SafetyLevel = Literal["curated", "unknown"]
type ExothermicityLevel = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class ClpBand:
    min_molarity: Decimal | None
    max_molarity: Decimal | None
    hazard_codes: tuple[str, ...] = ()
    pictograms: tuple[str, ...] = ()
    signal_word: Literal["danger", "warning"] | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PrepInputs:
    chemical_formula: str
    target_molarity: Decimal
    vol_per_group_ml: Decimal
    student_count: int
    students_per_group: int
    safety_factor: Decimal
    source_type: SourceType
    stock_molarity: Decimal | None
    solute_purity: Decimal


@dataclass(frozen=True, slots=True)
class PrepNumbers:
    formula_clean: str
    molar_mass_g_mol: Decimal
    total_groups: int
    total_volume_ml: Decimal
    moles_required: Decimal
    source_type: SourceType
    mass_g: Decimal | None = None
    stock_volume_ml: Decimal | None = None
    diluent_volume_ml: Decimal | None = None


@dataclass(frozen=True, slots=True)
class HazardEntry:
    key: str
    display_name: str
    hazard_codes: tuple[str, ...] = ()
    ppe: tuple[str, ...] = ()
    disposal: str | None = None
    notes: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    search_aliases: tuple[str, ...] = ()
    pubchem_cid: int | None = None
    sds_ref: str | None = None
    clp_bands: tuple[ClpBand, ...] = ()
    incompatibilities: tuple[str, ...] = ()
    exothermicity: ExothermicityLevel | None = None
    reaction_notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class HazardSdsData:
    sds_ref: str
    hazard_codes: tuple[str, ...]
    pictograms: tuple[str, ...]
    signal_word: Literal["danger", "warning"] | None = None
    clp_bands: tuple[ClpBand, ...] = ()
    incompatibilities: tuple[str, ...] = ()
    exothermicity: ExothermicityLevel | None = None
    reaction_notes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SdsFetchResult:
    sds_ref: str
    sds_bytes: bytes
    media_type: str
    source_url: str
    hazard_codes: tuple[str, ...]
    pictograms: tuple[str, ...]
    signal_word: Literal["danger", "warning"] | None = None
    clp_bands: tuple[ClpBand, ...] = ()
    incompatibilities: tuple[str, ...] = ()
    exothermicity: ExothermicityLevel | None = None
    reaction_notes: tuple[str, ...] = ()
    density_g_ml: Decimal | None = None
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SafetyResult:
    level: SafetyLevel
    entry: HazardEntry | None
