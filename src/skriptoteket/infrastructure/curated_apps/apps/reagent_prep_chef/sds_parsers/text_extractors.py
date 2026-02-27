"""Text extraction helpers for SDS-derived signals in Reagent Prep Chef.

This module implements lightweight regex-based extractors used on SDS PDF text:
- hazard codes (H-codes)
- pictograms (GHS codes)
- signal words (danger/warning)
- coarse document validation (is this likely an SDS?)

Related:
  - `sds_parsers/pdf_text.py` (PDF → text extraction)
  - `sds_pdf_fetcher.py` (downloads PDFs and uses `is_sds_document`)
  - `sds_result_builder.py` (merges PDF signals into the SDS result)
"""

from __future__ import annotations

import re
from typing import Literal

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    HAZARD_CODE_RE,
    NON_HAZARDOUS_RE,
    PICTOGRAM_RE,
    SDS_TITLE_RE,
    SIGNAL_WORD_RE,
)

_SDS_SECTION_RE = re.compile(
    r"^\s*(?:section|avsnitt)\s+(?P<num>1[0-6]|[1-9])\b",
    re.IGNORECASE | re.MULTILINE,
)
_SDS_NUMERIC_SECTION_RE = re.compile(
    r"^\s*(?P<num>1[0-6]|[1-9])\s*(?:[.:]|[-–])\s+(?P<title>[^\n]{3,120})$",
    re.IGNORECASE | re.MULTILINE,
)

_NON_SDS_GUIDE_RE = re.compile(
    r"\bHazard\s+Communication\s+Standard:\s*Safety\s+Data\s+Sheets\b"
    r"|\bThis\s+section\s+identifies\s+the\s+chemical\s+on\s+the\s+SDS\b",
    re.IGNORECASE,
)
_NON_SDS_FACT_SHEET_RE = re.compile(
    r"\bHazardous\s+Substance\s+Fact\s+Sheet\b",
    re.IGNORECASE,
)
_NON_SDS_CFR_RE = re.compile(
    r"\bPART\s+172[—-]\s*HAZARDOUS\s+MATERIALS\b",
    re.IGNORECASE,
)

_SDS_SECTION_TITLE_TOKENS = (
    "identification",
    "hazard",
    "composition",
    "first aid",
    "fire",
    "accidental release",
    "handling",
    "storage",
    "exposure",
    "personal protection",
    "physical",
    "chemical",
    "stability",
    "reactivity",
    "toxicological",
    "ecological",
    "disposal",
    "transport",
    "regulatory",
    "other information",
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

    if _NON_SDS_GUIDE_RE.search(text):
        return False
    if _NON_SDS_FACT_SHEET_RE.search(text):
        return False
    if _NON_SDS_CFR_RE.search(text):
        return False

    section_numbers: set[int] = set()
    for match in _SDS_SECTION_RE.finditer(text):
        section_numbers.add(int(match.group("num")))

    for match in _SDS_NUMERIC_SECTION_RE.finditer(text):
        title = match.group("title").strip().lower()
        if any(token in title for token in _SDS_SECTION_TITLE_TOKENS):
            section_numbers.add(int(match.group("num")))

    return len(section_numbers) >= 8
