from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import (
    ClpBand,
    ExothermicityLevel,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    extract_hazard_codes_from_text,
    extract_pictograms_from_text,
    extract_signal_word_from_text,
    parse_sds_clp_bands_from_text,
    parse_sds_heuristics_from_text,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_query_variants import (
    dedupe_preserve_order,
)

ProgressEmitter = Callable[[str], None]
SignalWord = Literal["danger", "warning"]


@dataclass(frozen=True, slots=True)
class GhsSnapshot:
    hazard_codes: list[str]
    pictograms: list[str]
    signal_word: SignalWord | None
    nonhazardous: bool
    sources: list[str]


def merge_pdf_ghs(*, snapshot: GhsSnapshot, pdf_text: str) -> GhsSnapshot:
    pdf_hazard_codes = extract_hazard_codes_from_text(pdf_text)
    pdf_pictograms = extract_pictograms_from_text(pdf_text)
    pdf_signal_word = extract_signal_word_from_text(pdf_text)

    hazard_codes = dedupe_preserve_order([*snapshot.hazard_codes, *pdf_hazard_codes])
    pictograms = dedupe_preserve_order([*snapshot.pictograms, *pdf_pictograms])
    has_danger = snapshot.signal_word == "danger" or pdf_signal_word == "danger"
    has_warning = snapshot.signal_word == "warning" or pdf_signal_word == "warning"
    signal_word: SignalWord | None
    if has_danger:
        signal_word = "danger"
    elif has_warning:
        signal_word = "warning"
    else:
        signal_word = None
    nonhazardous = snapshot.nonhazardous and not hazard_codes and signal_word is None

    return GhsSnapshot(
        hazard_codes=hazard_codes,
        pictograms=pictograms,
        signal_word=signal_word,
        nonhazardous=nonhazardous,
        sources=snapshot.sources,
    )


def merge_heuristics(
    *,
    pdf_text: str,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    return parse_sds_heuristics_from_text(pdf_text)


def build_clp_bands(
    *,
    pdf_text: str,
    molar_mass: Decimal,
    density_g_ml: Decimal,
    snapshot: GhsSnapshot,
    emit: ProgressEmitter | None = None,
) -> tuple[ClpBand, ...] | None:
    clp_bands = parse_sds_clp_bands_from_text(
        pdf_text,
        molar_mass_g_mol=molar_mass,
        density_g_ml=density_g_ml,
    )
    notes = ("Ej klassificerad enligt LCSS.",) if snapshot.nonhazardous else ()
    if not clp_bands:
        if snapshot.nonhazardous and not snapshot.hazard_codes:
            clp_bands = [
                ClpBand(
                    min_molarity=None,
                    max_molarity=None,
                    hazard_codes=(),
                    pictograms=tuple(snapshot.pictograms),
                    signal_word=snapshot.signal_word,
                    notes=notes,
                )
            ]
        else:
            if emit is not None:
                emit("candidate_missing_clp_bands")
            return None

    enriched = [
        ClpBand(
            min_molarity=band.min_molarity,
            max_molarity=band.max_molarity,
            hazard_codes=band.hazard_codes or tuple(snapshot.hazard_codes),
            pictograms=tuple(snapshot.pictograms),
            signal_word=snapshot.signal_word,
            notes=band.notes or notes,
        )
        for band in clp_bands
    ]
    enriched.sort(
        key=lambda band: (
            band.min_molarity is None,
            band.min_molarity or 0,
        ),
        reverse=True,
    )
    return tuple(enriched)
