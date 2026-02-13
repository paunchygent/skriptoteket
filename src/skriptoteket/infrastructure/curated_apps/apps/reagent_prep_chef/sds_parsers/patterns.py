from __future__ import annotations

import re

HAZARD_CODE_RE = re.compile(r"(?<!\w)H\s*[-–]?\s*\d{3}(?!\w)")
PICTOGRAM_RE = re.compile(r"\bGHS0\d\b", re.IGNORECASE)
SIGNAL_WORD_RE = re.compile(r"\b(danger|warning)\b", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*(section|avsnitt)\s+(\d{1,2})\b", re.IGNORECASE | re.MULTILINE)
ALT_SECTION_RE = re.compile(r"^\s*(\d{1,2})\s*(?:[.:]|[-–])\s+", re.IGNORECASE | re.MULTILINE)
SDS_TITLE_RE = re.compile(
    r"\b(safety\s+data\s+sheet|säkerhetsdatablad|sicherheitsdatenblatt|fiche\s+de\s+"
    r"donn(?:ée|e)s\s+de\s+s[ée]curit[ée])\b",
    re.IGNORECASE,
)
NON_HAZARDOUS_RE = re.compile(
    r"\b("
    r"not classified|not classif(?:ied|ed)|not hazardous|non[-\s]?hazardous|"
    r"not a hazardous substance|not a hazardous substance or mixture|"
    r"not dangerous|not classified as hazardous|"
    r"inte klassificerad|ej klassificerad|"
    r"inte farlig|ej farlig|ingen klassificering"
    r")\b",
    re.IGNORECASE,
)
