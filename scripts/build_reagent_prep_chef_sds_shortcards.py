"""Build SDS shortcards for Reagent Prep Chef from repo-owned markdown.

Purpose:
    Extract a school-focused SDS "shortcard" dataset from the committed markdown corpus.
    Shortcards are intended for portal autofill (identity, CLP, PPE, spill, incompatibility,
    and waste hints) while preserving raw markdown as the source of truth.

Relationships:
    - Reads `data/reagent_prep_chef/sds/index.json` for canonical SDS file selection.
    - Reads `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`
      for display names and default PPE hints.
    - Reads markdown files under `data/reagent_prep_chef/sds/markdown/`.
    - Writes `data/reagent_prep_chef/sds/shortcards.json`.
    - Writes parse/validation report and manual validation checklist under `.artifacts/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_INDEX_PATH = Path("data/reagent_prep_chef/sds/index.json")
DEFAULT_HAZARDS_PATH = Path(
    "src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json"
)
DEFAULT_MARKDOWN_DIR = Path("data/reagent_prep_chef/sds/markdown")
DEFAULT_OUTPUT_PATH = Path("data/reagent_prep_chef/sds/shortcards.json")
DEFAULT_REPORT_PATH = Path(".artifacts/reagent_prep_chef/sds-shortcards-report.json")
DEFAULT_MANUAL_CHECKLIST_PATH = Path(
    ".artifacts/reagent_prep_chef/sds-shortcards-manual-validation-checklist.md"
)

HEADING_PATTERN = re.compile(r"^\s*##\s+(.+?)\s*$")
SECTION_ONE_PATTERN = re.compile(r"(?:\bAVSNITT\s*1\b|\b1\.\s*Identifier)", re.IGNORECASE)
HTML_COMMENT_PATTERN = re.compile(r"<!--")
CAS_PATTERN = re.compile(
    r"\b(?:CAS(?:-nr| nummer)?|CAS no\.?)\b\s*[:]?[\s\n]*([0-9]{2,7}-[0-9]{2}-[0-9])",
    re.IGNORECASE,
)
EG_PATTERN = re.compile(
    r"\b(?:EG(?:-nr|[- ]nummer)?|EC(?:-no)?)\b\s*[:]?[\s\n]*([0-9]{3}-[0-9]{3}-[0-9])",
    re.IGNORECASE,
)
REACH_PATTERN = re.compile(
    r"\b(?:REACH|Registeringsnummer.*REACH)\b[^\n]*[:]?[\s\n]*([0-9]{2}-[0-9]{10}-[0-9]{2}-[A-Za-z0-9]{4})",
    re.IGNORECASE,
)
CLP_INDEX_PATTERN = re.compile(
    r"\b(?:Indexnummer.*CLP|CLP index)\b[^\n]*[:]?[\s\n]*([0-9]{3}-[0-9]{3}-[0-9]{2}-[A-Za-z0-9])",
    re.IGNORECASE,
)
H_CODE_PATTERN = re.compile(r"\bH[0-9]{3}\b")
P_CODE_PATTERN = re.compile(r"\bP[0-9]{3}(?:\+P?[0-9]{3})*\b")
GHS_PATTERN = re.compile(r"\bGHS[0-9]{2}\b", re.IGNORECASE)
PRODUCT_NO_PATTERN = re.compile(
    r"\b(?:Produktnummer|Produktkod|artikelnummer|Product code|Kat\.nr\.?)\b\s*[:]?[\s\n]*([0-9A-Za-z_.-]+)",
    re.IGNORECASE,
)
VERSION_PATTERN = re.compile(r"\bVersion\b\s*[:]?[\s\n]*([^\n]+)", re.IGNORECASE)
REPLACED_VERSION_PATTERN = re.compile(
    r"\bErsätter versionen från\b\s*[:]?[\s\n]*([0-9./-]+)", re.IGNORECASE
)
SIGNAL_WORD_PATTERN = re.compile(
    r"\b(?:Signalord|Signal word)\b\s*[:]?[\s\n]*(Fara|Varning|Danger|Warning)",
    re.IGNORECASE,
)
REVISION_PATTERNS = (
    re.compile(r"\bOmarbetning\b\s*[:]?[\s\n]*([0-9]{2}[./-][0-9]{2}[./-][0-9]{4})", re.IGNORECASE),
    re.compile(r"\bRevisionsdatum\b\s*[:]?[\s\n]*([0-9]{2}-[A-Za-z]{3}-[0-9]{4})", re.IGNORECASE),
    re.compile(
        r"\bdatum för sammanställning\b\s*[:]?[\s\n]*([0-9]{2}[./-][0-9]{2}[./-][0-9]{4})",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True, slots=True)
class ExtractionIssue:
    """Represents a parser or structure issue that requires manual review."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class SdsShortcard:
    """Portal-focused shortcard extracted from one SDS markdown document."""

    id: str
    sds_ref: str
    md_file_name: str
    source_provider: str
    supplier: str
    sds_title: str
    name_sv: str
    formula: str
    form_purity: str | None
    product_no: str | None
    cas: str | None
    eg: str | None
    reach_registration: str | None
    clp_index: str | None
    version: str | None
    revision_date: str | None
    replaced_version: str | None
    clp: dict[str, Any]
    ppe_default: list[str]
    ppe_notes: dict[str, str | None]
    spill_notes: str | None
    incompatibilities: list[str]
    waste_notes: str | None
    raw_markdown_path: str
    markdown_sha256: str
    parser_ground_truth: bool
    extraction_issues: list[dict[str, str]]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--hazards-path", type=Path, default=DEFAULT_HAZARDS_PATH)
    parser.add_argument("--markdown-dir", type=Path, default=DEFAULT_MARKDOWN_DIR)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--manual-checklist-path",
        type=Path,
        default=DEFAULT_MANUAL_CHECKLIST_PATH,
    )
    parser.add_argument(
        "--allow-issues",
        action="store_true",
        help=(
            "Allow completion when parser issues are detected. "
            "Without this flag, any issue triggers a non-zero exit and full manual validation."
        ),
    )
    return parser.parse_args()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_line(value: str) -> str:
    return " ".join(value.split())


def _markdown_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_heading_lines(text: str) -> list[str]:
    return [match.group(1).strip() for match in HEADING_PATTERN.finditer(text)]


def _extract_product_heading(text: str) -> str | None:
    headings = _extract_heading_lines(text)
    if not headings:
        return None
    for heading in headings:
        lowered = heading.casefold()
        if "säkerhetsdatablad" in lowered or "frivillig säkerhetsinformation" in lowered:
            continue
        if "avsnitt" in lowered:
            continue
        return _normalize_line(heading)
    return _normalize_line(headings[0])


def _extract_first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    value = match.group(1).strip()
    return _normalize_line(value) if value else None


def _extract_cas(text: str) -> str | None:
    labeled = _extract_first(CAS_PATTERN, text)
    if labeled:
        return labeled
    matches = re.findall(r"\b[0-9]{2,7}-[0-9]{2}-[0-9]\b", text)
    return matches[0] if matches else None


def _extract_eg(text: str) -> str | None:
    labeled = _extract_first(EG_PATTERN, text)
    if labeled:
        return labeled
    matches = re.findall(r"\b[0-9]{3}-[0-9]{3}-[0-9]\b", text)
    return matches[0] if matches else None


def _extract_date(text: str) -> str | None:
    for pattern in REVISION_PATTERNS:
        value = _extract_first(pattern, text)
        if not value:
            continue
        normalized = _normalize_date(value)
        if normalized:
            return normalized
    return None


def _normalize_date(raw: str) -> str | None:
    candidates = (
        "%d.%m.%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%Y-%m-%d",
    )
    for candidate in candidates:
        try:
            return datetime.strptime(raw, candidate).date().isoformat()
        except ValueError:
            continue
    return None


def _extract_section_text_by_number(text: str, section_number: int) -> str:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    for idx, line in enumerate(lines):
        heading_match = HEADING_PATTERN.match(line)
        if not heading_match:
            continue
        heading = heading_match.group(1)
        section_match = re.search(r"(?:AVSNITT|Section)\s*([0-9]{1,2})", heading, re.IGNORECASE)
        if section_match:
            try:
                starts.append((idx, int(section_match.group(1))))
            except ValueError:
                continue
            continue
        prefix_match = re.match(r"([0-9]{1,2})\.\s+", heading)
        if prefix_match:
            starts.append((idx, int(prefix_match.group(1))))

    target_positions = [position for position, number in starts if number == section_number]
    if not target_positions:
        return ""
    start_idx = target_positions[0]
    following = [
        position for position, number in starts if position > start_idx and number > section_number
    ]
    end_idx = following[0] if following else len(lines)
    return "\n".join(lines[start_idx:end_idx])


def _extract_value_after_labels(text: str, labels: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    label_patterns = [re.compile(label, re.IGNORECASE) for label in labels]
    for idx, line in enumerate(lines):
        matched = next((pattern for pattern in label_patterns if pattern.search(line)), None)
        if matched is None:
            continue

        inline_match = re.search(r":\s*(.+)$", line)
        if inline_match:
            value = _normalize_line(inline_match.group(1))
            if value:
                return value

        for candidate_line in lines[idx + 1 : idx + 7]:
            candidate = candidate_line.strip()
            if not candidate:
                continue
            if candidate.startswith("## "):
                break
            return _normalize_line(candidate)
    return None


def _extract_h_codes(text: str) -> list[str]:
    return sorted(set(H_CODE_PATTERN.findall(text)))


def _extract_p_codes(text: str) -> list[str]:
    values: set[str] = set()
    for match in P_CODE_PATTERN.findall(text):
        normalized = match.upper()
        normalized = normalized.replace("+", "+P")
        normalized = normalized.replace("PP", "P")
        values.add(normalized)
    return sorted(values)


def _extract_ghs_codes(text: str, h_codes: list[str]) -> list[str]:
    codes = {code.upper() for code in GHS_PATTERN.findall(text)}

    if any(code in {"H314", "H318", "H290"} for code in h_codes):
        codes.add("GHS05")
    if any(code.startswith(("H300", "H301", "H310", "H330")) for code in h_codes):
        codes.add("GHS06")
    if any(code in {"H315", "H319", "H335", "H317"} for code in h_codes):
        codes.add("GHS07")
    if any(code.startswith(("H340", "H350", "H360", "H370", "H372")) for code in h_codes):
        codes.add("GHS08")
    if any(code.startswith(("H400", "H410", "H411", "H412")) for code in h_codes):
        codes.add("GHS09")

    return sorted(codes)


def _extract_signal_word(text: str, h_codes: list[str]) -> str | None:
    explicit = _extract_first(SIGNAL_WORD_PATTERN, text)
    if explicit:
        lowered = explicit.casefold()
        if lowered in {"fara", "danger"}:
            return "Fara"
        if lowered in {"varning", "warning"}:
            return "Varning"
        return explicit
    if any(code in {"H314", "H318", "H330", "H301"} for code in h_codes):
        return "Fara"
    return None


def _extract_sentence_hits(text: str, keywords: tuple[str, ...], *, limit: int = 2) -> list[str]:
    normalized = re.sub(r"\s+", " ", text)
    candidates = re.split(r"(?<=[.!?])\s+", normalized)
    hits: list[str] = []
    for sentence in candidates:
        candidate = sentence.strip()
        if len(candidate) < 8:
            continue
        lowered = candidate.casefold()
        if not any(keyword.casefold() in lowered for keyword in keywords):
            continue
        if candidate not in hits:
            hits.append(candidate)
        if len(hits) >= limit:
            break
    return hits


def _provider_to_supplier(provider: str) -> str:
    mapping = {
        "carlroth": "Carl Roth",
        "fishersci": "Fisher Scientific",
        "chemicalbook": "ChemicalBook",
        "external": "External supplier",
        "eastharbour": "East Harbour Group",
    }
    key = provider.strip().lower()
    return mapping.get(key, provider)


def _clean_formula_from_display_name(display_name: str, fallback: str) -> str:
    inner = re.search(r"\(([^)]+)\)", display_name)
    if inner:
        return inner.group(1).strip()
    return fallback


def _build_identity_name(*, markdown_text: str, display_name: str, fallback_key: str) -> str:
    extracted = _extract_value_after_labels(
        markdown_text,
        labels=(
            r"^Namnet på ämnet$",
            r"^Produktnamn$",
            r"^GHS-produkt$",
        ),
    )
    if extracted:
        return extracted

    heading = _extract_product_heading(markdown_text)
    if heading:
        return heading

    cleaned_display = re.sub(r"\s*\([^)]*\)\s*", " ", display_name).strip()
    return cleaned_display or fallback_key


def _derive_form_purity(*, product_heading: str | None, name_sv: str) -> str | None:
    if not product_heading:
        return None
    candidate = product_heading
    if candidate.casefold().startswith(name_sv.casefold()):
        candidate = candidate[len(name_sv) :].strip(" ,;-")
    if not candidate:
        return None
    if candidate.casefold() == name_sv.casefold():
        return None
    return candidate


def _build_shortcard_id(*, sds_ref: str, provider: str, product_no: str | None) -> str:
    base = f"{sds_ref}_{provider}_{product_no or 'unknown'}"
    return re.sub(r"[^0-9A-Za-z_]+", "_", base)


def _validate_markdown_structure(text: str) -> list[ExtractionIssue]:
    issues: list[ExtractionIssue] = []
    first_non_empty = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_non_empty.startswith("## "):
        issues.append(
            ExtractionIssue(
                code="structure_missing_h2_start",
                message="Markdown must start with a level-2 heading (`## ...`).",
            )
        )
    if SECTION_ONE_PATTERN.search(text) is None:
        issues.append(
            ExtractionIssue(
                code="structure_missing_section_1",
                message="Markdown is missing section-1 anchor (AVSNITT 1 or 1. Identifiering).",
            )
        )
    if HTML_COMMENT_PATTERN.search(text):
        issues.append(
            ExtractionIssue(
                code="structure_contains_html_comment",
                message="Markdown contains HTML comments (possible conversion artifact).",
            )
        )
    return issues


def _extract_shortcard(
    *,
    sds_ref: str,
    provider: str,
    md_file_name: str,
    markdown_text: str,
    display_name: str,
    ppe_default: list[str],
) -> tuple[SdsShortcard, list[ExtractionIssue]]:
    issues = _validate_markdown_structure(markdown_text)

    formula = _clean_formula_from_display_name(display_name, sds_ref)
    identity_name = _build_identity_name(
        markdown_text=markdown_text,
        display_name=display_name,
        fallback_key=sds_ref,
    )
    product_heading = _extract_product_heading(markdown_text)
    form_purity = _derive_form_purity(product_heading=product_heading, name_sv=identity_name)

    product_no = _extract_first(PRODUCT_NO_PATTERN, markdown_text)
    cas = _extract_cas(markdown_text)
    eg = _extract_eg(markdown_text)
    reach_registration = _extract_first(REACH_PATTERN, markdown_text)
    clp_index = _extract_first(CLP_INDEX_PATTERN, markdown_text)
    version = _extract_first(VERSION_PATTERN, markdown_text)
    revision_date = _extract_date(markdown_text)
    replaced_version = _extract_first(REPLACED_VERSION_PATTERN, markdown_text)

    section_two = _extract_section_text_by_number(markdown_text, 2) or markdown_text
    section_six = _extract_section_text_by_number(markdown_text, 6) or markdown_text
    section_eight = _extract_section_text_by_number(markdown_text, 8) or markdown_text
    section_ten = _extract_section_text_by_number(markdown_text, 10) or markdown_text
    section_thirteen = _extract_section_text_by_number(markdown_text, 13) or markdown_text

    h_codes = _extract_h_codes(section_two)
    p_codes = _extract_p_codes(section_two)
    pictograms = _extract_ghs_codes(section_two, h_codes)
    signal_word = _extract_signal_word(section_two, h_codes)

    classification_tokens = sorted(
        set(re.findall(r"\b[A-Za-z]{2,}(?:\.[A-Za-z]{2,})?\s*[0-9][A-Za-z]?\b", section_two))
    )

    eye_hits = _extract_sentence_hits(
        section_eight,
        keywords=("ögon", "eye protection", "korgglasögon", "ansiktsskydd"),
        limit=1,
    )
    hand_hits = _extract_sentence_hits(
        section_eight,
        keywords=("handsk", "glove", "butyl", "nitril"),
        limit=1,
    )
    respirator_hits = _extract_sentence_hits(
        section_eight,
        keywords=("andnings", "respir", "partikelfilter", "p1", "p2", "p3"),
        limit=1,
    )

    spill_hits = _extract_sentence_hits(
        section_six,
        keywords=("mekanisk", "damm", "avlopp", "ventil", "spills", "spill"),
        limit=2,
    )
    incompatibility_hits = _extract_sentence_hits(
        section_ten,
        keywords=("oförenlig", "våldsam", "stark", "oxid", "alkali", "reaktion"),
        limit=3,
    )
    waste_hits = _extract_sentence_hits(
        section_thirteen,
        keywords=("farligt avfall", "avlopp", "avfall", "waste"),
        limit=2,
    )

    if not identity_name:
        issues.append(
            ExtractionIssue(
                code="missing_identity_name", message="Could not extract identity name."
            )
        )
    if not product_no and not cas and not eg:
        issues.append(
            ExtractionIssue(
                code="missing_identity_identifiers",
                message="Could not extract product number, CAS, or EG identifier.",
            )
        )

    shortcard = SdsShortcard(
        id=_build_shortcard_id(sds_ref=sds_ref, provider=provider, product_no=product_no),
        sds_ref=sds_ref,
        md_file_name=md_file_name,
        source_provider=provider,
        supplier=_provider_to_supplier(provider),
        sds_title=f"SDS: {sds_ref}",
        name_sv=identity_name,
        formula=formula,
        form_purity=form_purity,
        product_no=product_no,
        cas=cas,
        eg=eg,
        reach_registration=reach_registration,
        clp_index=clp_index,
        version=version,
        revision_date=revision_date,
        replaced_version=replaced_version,
        clp={
            "classification": classification_tokens,
            "h_codes": h_codes,
            "p_codes": p_codes,
            "pictograms": pictograms,
            "signal_word": signal_word,
        },
        ppe_default=ppe_default,
        ppe_notes={
            "eyes": eye_hits[0] if eye_hits else None,
            "hands": hand_hits[0] if hand_hits else None,
            "respirator": respirator_hits[0] if respirator_hits else None,
        },
        spill_notes=" ".join(spill_hits) if spill_hits else None,
        incompatibilities=incompatibility_hits,
        waste_notes=" ".join(waste_hits) if waste_hits else None,
        raw_markdown_path=f"data/reagent_prep_chef/sds/markdown/{md_file_name}",
        markdown_sha256=_markdown_sha256(markdown_text),
        parser_ground_truth=False,
        extraction_issues=[asdict(item) for item in issues],
    )
    return shortcard, issues


def _build_manual_checklist(
    *,
    markdown_file_names: list[str],
    issue_counts_by_code: dict[str, int],
) -> str:
    lines: list[str] = []
    lines.append("# SDS manual validation checklist\n\n")
    lines.append(
        "Parser output is never ground truth. Raw SDS markdown remains canonical source-of-truth.\n\n"
    )
    lines.append("## Trigger\n\n")
    lines.append(
        "Parser/structure issues were detected. Invariant: manually validate **all** SDS markdown files.\n\n"
    )
    lines.append("## Issue summary\n\n")
    for code in sorted(issue_counts_by_code):
        lines.append(f"- `{code}`: {issue_counts_by_code[code]}\n")
    lines.append("\n## Full-file review checklist\n\n")
    for name in markdown_file_names:
        lines.append(f"- [ ] `{name}`\n")
    return "".join(lines)


def _build_manual_not_required_note() -> str:
    return (
        "# SDS manual validation checklist\n\n"
        "No parser/structure issues were detected in this run.\n\n"
        "Invariant remains active: parser output is never ground truth, and full manual validation "
        "is required whenever issues are detected.\n"
    )


def main() -> None:
    args = _parse_args()

    index_payload = _load_json(args.index_path)
    if not isinstance(index_payload, dict):
        raise SystemExit(f"Unexpected index payload: {args.index_path}")
    entries_payload = index_payload.get("entries")
    if not isinstance(entries_payload, dict):
        raise SystemExit(f"Unexpected index entries payload: {args.index_path}")

    hazards_payload = _load_json(args.hazards_path)
    if not isinstance(hazards_payload, list):
        raise SystemExit(f"Unexpected hazards payload: {args.hazards_path}")
    hazards_by_key = {
        str(item.get("key")): item
        for item in hazards_payload
        if isinstance(item, dict) and isinstance(item.get("key"), str)
    }

    shortcards: list[SdsShortcard] = []
    issue_counts_by_code: dict[str, int] = {}
    files_with_issues: list[str] = []

    for sds_ref in sorted(entries_payload):
        entry = entries_payload[sds_ref]
        if not isinstance(entry, dict):
            continue
        md_file_name = str(entry.get("md_file_name") or "").strip()
        if not md_file_name:
            continue
        md_path = args.markdown_dir / md_file_name
        if not md_path.is_file():
            issue = ExtractionIssue(
                code="missing_markdown_file",
                message=f"Missing markdown file referenced by index: {md_file_name}",
            )
            issue_counts_by_code[issue.code] = issue_counts_by_code.get(issue.code, 0) + 1
            files_with_issues.append(md_file_name)
            continue

        markdown_text = md_path.read_text(encoding="utf-8")
        hazard = hazards_by_key.get(sds_ref, {})
        display_name = str(hazard.get("display_name") or sds_ref)
        ppe_default = [
            str(item).strip()
            for item in (hazard.get("ppe") if isinstance(hazard, dict) else [])
            if isinstance(item, str) and item.strip()
        ]
        provider = str(entry.get("provider") or "unknown")
        shortcard, issues = _extract_shortcard(
            sds_ref=sds_ref,
            provider=provider,
            md_file_name=md_file_name,
            markdown_text=markdown_text,
            display_name=display_name,
            ppe_default=ppe_default,
        )
        shortcards.append(shortcard)

        if issues:
            files_with_issues.append(md_file_name)
            for issue in issues:
                issue_counts_by_code[issue.code] = issue_counts_by_code.get(issue.code, 0) + 1

    manual_validation_required = bool(issue_counts_by_code)
    markdown_file_names = sorted(
        path.name for path in args.markdown_dir.glob("*.md") if "__" in path.stem
    )

    payload = {
        "version": 1,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "parser_ground_truth": False,
        "manual_validation": {
            "required": manual_validation_required,
            "scope": "all_files" if manual_validation_required else "none",
            "trigger_issue_counts": issue_counts_by_code,
            "invariant": (
                "Never trust parser output as ground truth; raw SDS markdown is canonical. "
                "If any issue arises, manually validate all files."
            ),
        },
        "entries": [asdict(item) for item in sorted(shortcards, key=lambda item: item.sds_ref)],
    }

    report_payload = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "shortcards_built": len(shortcards),
            "files_with_issues": len(set(files_with_issues)),
            "manual_validation_required": manual_validation_required,
        },
        "issue_counts": issue_counts_by_code,
        "files_with_issues": sorted(set(files_with_issues)),
    }

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    args.manual_checklist_path.parent.mkdir(parents=True, exist_ok=True)
    checklist = (
        _build_manual_checklist(
            markdown_file_names=markdown_file_names,
            issue_counts_by_code=issue_counts_by_code,
        )
        if manual_validation_required
        else _build_manual_not_required_note()
    )
    args.manual_checklist_path.write_text(checklist, encoding="utf-8")

    print(f"[sds_shortcards] wrote={args.output_path}")
    print(f"[sds_shortcards_report] wrote={args.report_path}")
    print(f"[sds_shortcards_manual_checklist] wrote={args.manual_checklist_path}")
    print(
        "[sds_shortcards_invariant] parser_ground_truth=false "
        f"manual_validation_required={manual_validation_required}"
    )

    if manual_validation_required and not args.allow_issues:
        raise SystemExit(
            "Parser/structure issues detected. Manual validation of ALL markdown files is required."
        )


if __name__ == "__main__":
    main()
