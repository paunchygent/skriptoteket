from __future__ import annotations

import re
from io import BytesIO
from typing import Iterable, Literal

from pypdf import PdfReader

from skriptoteket.domain.curated_apps.reagent_prep_chef.models import ExothermicityLevel

_HAZARD_CODE_RE = re.compile(r"\bH\d{3}\b")
_PICTOGRAM_RE = re.compile(r"\bGHS0\d\b", re.IGNORECASE)
_SIGNAL_WORD_RE = re.compile(r"\b(danger|warning)\b", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*(section|avsnitt)\s+(\d{1,2})\b", re.IGNORECASE)


def extract_pubchem_ghs(
    pug_view: dict,
) -> tuple[list[str], list[str], Literal["danger", "warning"] | None]:
    ghs_section = _find_section_by_heading(pug_view, "GHS Classification")
    if ghs_section is None:
        return ([], [], None)

    hazard_codes: list[str] = []
    pictograms: list[str] = []
    signal_word: Literal["danger", "warning"] | None = None

    for info in _iter_information(ghs_section):
        name = info.get("Name")
        value = info.get("Value", {})
        if name == "GHS Hazard Statements":
            for text in _iter_string_values(value):
                hazard_codes.extend(_HAZARD_CODE_RE.findall(text))
        elif name == "Pictogram(s)":
            for entry in _iter_markup_values(value):
                url = entry.get("URL")
                if not isinstance(url, str):
                    continue
                code = _extract_pictogram_code(url)
                if code:
                    pictograms.append(code)
        elif name == "Signal":
            for text in _iter_string_values(value):
                normalized = text.strip().lower()
                if normalized == "danger":
                    signal_word = "danger"
                elif normalized == "warning":
                    signal_word = "warning"

    hazard_codes = sorted(set(hazard_codes))
    pictograms = sorted(set(pictograms))
    return (hazard_codes, pictograms, signal_word)


def extract_candidate_urls(payload: object) -> list[str]:
    urls: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            if value.startswith("http://") or value.startswith("https://"):
                urls.add(value)

    walk(payload)
    return sorted(urls)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    text_chunks: list[str] = []
    for page in reader.pages:
        extracted = page.extract_text() or ""
        if extracted:
            text_chunks.append(extracted)
    return "\n".join(text_chunks)


def extract_hazard_codes_from_text(text: str) -> list[str]:
    return sorted(set(_HAZARD_CODE_RE.findall(text)))


def extract_pictograms_from_text(text: str) -> list[str]:
    return sorted({code.upper() for code in _PICTOGRAM_RE.findall(text)})


def extract_signal_word_from_text(text: str) -> Literal["danger", "warning"] | None:
    for line in text.splitlines():
        lowered = line.lower()
        if "signal word" in lowered or "signalord" in lowered:
            match = _SIGNAL_WORD_RE.search(line)
            if match:
                value = match.group(1).lower()
                if value == "danger":
                    return "danger"
                if value == "warning":
                    return "warning"
    return None


def parse_sds_heuristics_from_pdf(
    pdf_bytes: bytes,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    text = extract_pdf_text(pdf_bytes)
    return parse_sds_heuristics_from_text(text)


def parse_sds_heuristics_from_text(
    text: str,
) -> tuple[list[str], ExothermicityLevel | None, list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    section_text = _extract_section(lines, section_number="10")
    if not section_text:
        section_text = "\n".join(lines)

    incompatibilities = _extract_field_values(
        section_text,
        labels=("Incompatible materials", "Incompatibilities", "Inkompatibla material"),
    )
    reaction_notes = _extract_field_values(
        section_text,
        labels=(
            "Hazardous reactions",
            "Hazardous decomposition products",
            "Conditions to avoid",
            "Farliga reaktioner",
            "Farliga sönderdelningsprodukter",
        ),
    )

    if not incompatibilities:
        incompatibilities = _scan_for_keywords(
            lines,
            keywords=("incompatible", "incompatib", "inkompatib"),
        )

    if not reaction_notes:
        reaction_notes = _scan_for_keywords(
            lines,
            keywords=(
                "hazardous reaction",
                "dangerous reaction",
                "stability",
                "stable",
                "conditions to avoid",
                "farliga reaktioner",
                "stabil",
            ),
        )
    exothermicity = _infer_exothermicity(section_text)

    return (incompatibilities, exothermicity, reaction_notes)


def _find_section_by_heading(payload: dict, heading: str) -> dict | None:
    def walk(section: dict) -> dict | None:
        if section.get("TOCHeading") == heading:
            return section
        for child in section.get("Section", []) or []:
            if isinstance(child, dict):
                found = walk(child)
                if found is not None:
                    return found
        return None

    record = payload.get("Record")
    if not isinstance(record, dict):
        return None
    for section in record.get("Section", []) or []:
        if isinstance(section, dict):
            found = walk(section)
            if found is not None:
                return found
    return None


def _iter_information(section: dict) -> Iterable[dict]:
    for info in section.get("Information", []) or []:
        if isinstance(info, dict):
            yield info
    for child in section.get("Section", []) or []:
        if isinstance(child, dict):
            yield from _iter_information(child)


def _iter_string_values(value: dict) -> Iterable[str]:
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return
    for item in strings:
        if isinstance(item, dict):
            text = item.get("String")
            if isinstance(text, str):
                yield text


def _iter_markup_values(value: dict) -> Iterable[dict]:
    strings = value.get("StringWithMarkup")
    if not isinstance(strings, list):
        return
    for item in strings:
        if isinstance(item, dict):
            for markup in item.get("Markup", []) or []:
                if isinstance(markup, dict):
                    yield markup


def _extract_pictogram_code(url: str) -> str | None:
    match = re.search(r"(GHS\d{2})", url, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper()


def _extract_section(lines: list[str], section_number: str) -> str:
    buffer: list[str] = []
    capture = False
    for line in lines:
        match = _SECTION_RE.match(line)
        if match:
            number = match.group(2)
            capture = number == section_number
            if number != section_number and buffer:
                break
            continue
        if capture:
            buffer.append(line)
    return "\n".join(buffer)


def _extract_field_values(section_text: str, labels: Iterable[str]) -> list[str]:
    values: list[str] = []
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:\-]\s*(.+)", re.IGNORECASE)
        for index, line in enumerate(lines):
            match = pattern.search(line)
            if match:
                value = match.group(1).strip()
                if value:
                    values.append(value)
                continue
            if label.lower() in line.lower():
                next_value = _next_nonempty_line(lines, index + 1)
                if next_value and not _line_contains_label(next_value, labels):
                    values.append(next_value)
    return _normalize_list(values)


def _line_contains_label(line: str, labels: Iterable[str]) -> bool:
    lowered = line.lower()
    return any(label.lower() in lowered for label in labels)


def _next_nonempty_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index:]:
        if line:
            return line
    return None


def _scan_for_keywords(lines: list[str], *, keywords: Iterable[str]) -> list[str]:
    results: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            results.append(line)
    return _normalize_list(results)


def _normalize_list(values: list[str]) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    deduped = []
    seen = set()
    for value in cleaned:
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(value)
    return deduped


def _infer_exothermicity(section_text: str) -> ExothermicityLevel | None:
    lowered = section_text.lower()
    if "exotherm" in lowered:
        if "violently" in lowered or "kraftigt" in lowered:
            return "high"
        return "medium"
    if "endotherm" in lowered:
        return "none"
    return None
