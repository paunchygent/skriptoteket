from __future__ import annotations

from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    ALT_SECTION_RE,
    SECTION_RE,
)


def extract_section(lines: list[str], section_number: str) -> str:
    """Extract a numbered SDS section from a list of lines."""
    buffer: list[str] = []
    capture = False
    for line in lines:
        match = SECTION_RE.match(line)
        if match:
            number = match.group(2)
        else:
            alt_match = ALT_SECTION_RE.match(line)
            if alt_match:
                number = alt_match.group(1)
            else:
                number = None
        if number:
            capture = number == section_number
            if number != section_number and buffer:
                break
            continue
        if capture:
            buffer.append(line)
    return "\n".join(buffer)
