from __future__ import annotations

import re
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    ALT_SECTION_RE,
    HAZARD_CODE_RE,
    NON_HAZARDOUS_RE,
    PICTOGRAM_RE,
    SDS_TITLE_RE,
    SECTION_RE,
    SIGNAL_WORD_RE,
)


def extract_hazard_codes_from_text(text: str) -> list[str]:
    """Extract normalized H-codes from SDS text."""
    normalized_codes: set[str] = set()
    for match in HAZARD_CODE_RE.findall(text):
        normalized = re.sub(r"[^A-Za-z0-9]", "", match).upper()
        if re.fullmatch(r"H\d{3}", normalized):
            normalized_codes.add(normalized)
    return sorted(normalized_codes)


def extract_pictograms_from_text(text: str) -> list[str]:
    """Extract GHS pictogram codes from SDS text."""
    return sorted({code.upper() for code in PICTOGRAM_RE.findall(text)})


def extract_signal_word_from_text(text: str) -> Literal["danger", "warning"] | None:
    """Extract signal word (danger/warning) from SDS text."""
    for line in text.splitlines():
        lowered = line.lower()
        if "signal word" in lowered or "signalord" in lowered:
            match = SIGNAL_WORD_RE.search(line)
            if match:
                value = match.group(1).lower()
                if value == "danger":
                    return "danger"
                if value == "warning":
                    return "warning"
    return None


def is_nonhazardous_from_text(text: str) -> bool:
    """Return True if text indicates the substance is not classified as hazardous."""
    return bool(NON_HAZARDOUS_RE.search(text))


def is_sds_document(text: str) -> bool:
    """Return True if the text looks like a full SDS document."""
    if not SDS_TITLE_RE.search(text):
        return False
    return bool(SECTION_RE.search(text) or ALT_SECTION_RE.search(text))
