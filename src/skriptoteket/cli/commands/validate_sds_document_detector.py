"""Validate the SDS PDF document detector against real-world PDFs.

Purpose:
  - Provide a data-first sanity check for `is_sds_document()` (the coarse SDS-vs-non-SDS
    classifier used by the Reagent Prep Chef SDS pipeline).
  - Prevent "vibe fixes" by pinning root causes when we tighten/loosen document heuristics.

This command is intentionally network-backed (for local validation only). It downloads a pinned
set of known SDS and known non-SDS PDFs and reports whether `is_sds_document()` agrees with the
expected classification, including debug signals for why.

Related:
  - `sds_pdf_fetcher.py` (uses `is_sds_document` to accept/reject candidates)
  - `sds_parsers/text_extractors.py` (`is_sds_document` implementation)
  - PR-0062 Slice 6.x assumption validation docs under `docs/backlog/prs/`
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import typer

from skriptoteket.config import Settings
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers import (
    text_extractors as sds_text_extractors,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.patterns import (
    SDS_TITLE_RE,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_parsers.pdf_text import (
    extract_pdf_text,
)
from skriptoteket.infrastructure.curated_apps.apps.reagent_prep_chef.sds_pdf_fetcher import (
    looks_like_pdf,
)

_NON_SDS_CFR_RE = sds_text_extractors._NON_SDS_CFR_RE
_NON_SDS_FACT_SHEET_RE = sds_text_extractors._NON_SDS_FACT_SHEET_RE
_NON_SDS_GUIDE_RE = sds_text_extractors._NON_SDS_GUIDE_RE
_SDS_NUMERIC_SECTION_RE = sds_text_extractors._SDS_NUMERIC_SECTION_RE
_SDS_SECTION_RE = sds_text_extractors._SDS_SECTION_RE
_SDS_SECTION_TITLE_TOKENS = sds_text_extractors._SDS_SECTION_TITLE_TOKENS
is_sds_document = sds_text_extractors.is_sds_document


@dataclass(frozen=True, slots=True)
class DetectorCase:
    """One real-world PDF classification case."""

    name: str
    url: str
    expected_is_sds: bool
    notes: str


DEFAULT_CASES: tuple[DetectorCase, ...] = (
    # Known non-SDS PDFs (previous false positives in the pipeline).
    DetectorCase(
        name="osha_sds_format_guidance",
        url="https://www.osha.gov/sites/default/files/publications/OSHA3514.pdf",
        expected_is_sds=False,
        notes="OSHA guidance about SDS format; not a substance SDS.",
    ),
    DetectorCase(
        name="cfr_hazmat_regulations",
        url=(
            "https://www.govinfo.gov/content/pkg/CFR-2020-title49-vol2/pdf/"
            "CFR-2020-title49-vol2-part172.pdf"
        ),
        expected_is_sds=False,
        notes="CFR hazmat regulations PDF; not a substance SDS.",
    ),
    DetectorCase(
        name="nj_rtk_fact_sheet_benzoic_acid",
        url="https://www.nj.gov/health/eoh/rtkweb/documents/fs/0209.pdf",
        expected_is_sds=False,
        notes="NJ Right-to-Know fact sheet; contains 'Hazardous Substance Fact Sheet'.",
    ),
    DetectorCase(
        name="cas_terms_pdf",
        url="https://www.cas.org/sites/default/files/documents/chemical-safety-library-terms.pdf",
        expected_is_sds=False,
        notes="CAS terms/marketing PDF; not SDS.",
    ),
    DetectorCase(
        name="nj_rtk_act",
        url="https://www.nj.gov/health/workplacehealthandsafety/documents/right-to-know/rtkact.pdf",
        expected_is_sds=False,
        notes="NJ Right-to-Know Act legal text; not SDS.",
    ),
    # Known SDS PDFs (curated linkouts used for PR-0062 Slice 6.4).
    DetectorCase(
        name="koh_sds_columbus",
        url="https://www.columbuschemical.com/MSDS/SDS/Potassium%20Hydroxide%2C%20Pellet%2C%20ACS%204325.pdf",
        expected_is_sds=True,
        notes="KOH SDS (Columbus Chemical Industries).",
    ),
    DetectorCase(
        name="h2o2_sds_columbus",
        url=(
            "https://www.columbuschemical.com/MSDS/SDS/"
            "Hydrogen%20Peroxide%2030%25%2C%20ACS%2C%20Stabilized%202665.pdf"
        ),
        expected_is_sds=True,
        notes="H2O2 SDS (Columbus Chemical Industries).",
    ),
    DetectorCase(
        name="h2so4_sds_carl_roth",
        url=(
            "https://www.carlroth.com/medias/SDB-9789-DE-EN.pdf?"
            "context=bWFzdGVyfHNlY3VyaXR5RGF0YXNoZWV0c3wzMjc1NDF8YXBwbGljYXRpb24vcGRm"
            "fGFEVXpMMmd4TWk4NU1qTXpNRGcyTWpFNE1qY3dMMU5FUWw4NU56ZzVYMFJGWDBWT0xuQmta"
            "Z3wxMjZkODk0ZjE1MmU4ZTkyMjRiOGViZmZhZDI2OWE5M2U2Mjg5NmZjOTZmZWExYzQ2NjE5"
            "YWYwMzFlODA4YjI2"
        ),
        expected_is_sds=True,
        notes="H2SO4 SDS (Carl Roth; EU REACH/CLP-style).",
    ),
    DetectorCase(
        name="h2so4_sds_columbus_mentions_right_to_know",
        url="https://www.columbuschemical.com/MSDS/SDS/Sulfuric%20Acid%2096%25%20ACS%205672.pdf",
        expected_is_sds=True,
        notes="H2SO4 SDS that mentions 'Right to Know' in regulatory section (regression guard).",
    ),
)


def validate_sds_document_detector(
    out_path: Path = typer.Option(
        Path(".artifacts/sds-cache/sds-document-detector-report.json"),
        "--out",
        help="Where to write the JSON validation report.",
    ),
    cases_path: Path | None = typer.Option(
        None,
        "--cases",
        help=(
            "Optional JSON file that defines cases as a list of "
            "{name,url,expected_is_sds,notes} objects. Defaults to built-in cases."
        ),
    ),
    timeout_seconds: float = typer.Option(
        30.0,
        "--timeout-seconds",
        min=1.0,
        help="HTTP timeout per case.",
    ),
) -> None:
    """Validate `is_sds_document` against a small real-world PDF suite."""
    settings = Settings()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cases = _load_cases(cases_path=cases_path)

    results: list[dict[str, Any]] = []
    ok = 0
    failed = 0
    skipped = 0

    with httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={"User-Agent": settings.SDS_FETCH_USER_AGENT},
    ) as client:
        for case in cases:
            result = _run_case(client=client, case=case)
            results.append(result)
            if result["status"] == "ok":
                ok += 1
            elif result["status"] == "fail":
                failed += 1
            else:
                skipped += 1

            expected = case.expected_is_sds
            actual = result.get("actual_is_sds")
            if actual is None:
                typer.echo(f"SKIP {case.name}: {result.get('error')}")
            elif expected == actual:
                typer.echo(f"OK   {case.name}: expected={expected} actual={actual}")
            else:
                typer.echo(
                    f"FAIL {case.name}: expected={expected} actual={actual} "
                    f"(reason={result.get('reason')})"
                )

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "cases_count": len(cases),
        "summary": {"ok": ok, "fail": failed, "skipped": skipped, "total": len(cases)},
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    typer.echo(f"Wrote report: {out_path}")


def _load_cases(*, cases_path: Path | None) -> list[DetectorCase]:
    if cases_path is None:
        return list(DEFAULT_CASES)
    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise typer.BadParameter("Cases JSON must be a list of objects.")
    cases: list[DetectorCase] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise typer.BadParameter(f"Case at index {index} must be an object.")
        try:
            cases.append(
                DetectorCase(
                    name=str(raw["name"]),
                    url=str(raw["url"]),
                    expected_is_sds=bool(raw["expected_is_sds"]),
                    notes=str(raw.get("notes") or ""),
                )
            )
        except KeyError as exc:
            raise typer.BadParameter(f"Case at index {index} missing field: {exc}") from exc
    return cases


def _run_case(*, client: httpx.Client, case: DetectorCase) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": case.name,
        "url": case.url,
        "expected_is_sds": case.expected_is_sds,
        "notes": case.notes,
        "status": "skip",
        "actual_is_sds": None,
        "reason": None,
        "error": None,
    }
    try:
        response = client.get(case.url)
    except httpx.HTTPError as exc:
        result["error"] = f"http_error: {exc}"
        return result

    result["http_status"] = response.status_code
    result["content_type"] = response.headers.get("content-type")
    result["final_url"] = str(response.url)

    if response.status_code != 200:
        result["error"] = f"http_status: {response.status_code}"
        return result

    body = response.content
    if not looks_like_pdf(body=body):
        result["error"] = "not_pdf_magic"
        result["body_head"] = body[:32].decode("utf-8", errors="replace")
        return result

    text = extract_pdf_text(body)
    actual = is_sds_document(text)
    result["actual_is_sds"] = actual

    has_title = bool(SDS_TITLE_RE.search(text))
    result["debug"] = {
        "text_len": len(text),
        "text_head": text[:240],
        "has_sds_title": has_title,
        "non_sds_guide_match": bool(_NON_SDS_GUIDE_RE.search(text)),
        "non_sds_fact_sheet_match": bool(_NON_SDS_FACT_SHEET_RE.search(text)),
        "non_sds_cfr_match": bool(_NON_SDS_CFR_RE.search(text)),
        "mentions_right_to_know": ("right to know" in text.lower()),
        "section_numbers": _extract_section_numbers(text=text),
    }

    expected = case.expected_is_sds
    if expected == actual:
        result["status"] = "ok"
        return result

    result["status"] = "fail"
    result["reason"] = _classify_mismatch(expected=expected, actual=actual, text=text)
    return result


def _extract_section_numbers(*, text: str) -> list[int]:
    section_numbers: set[int] = set()
    for match in _SDS_SECTION_RE.finditer(text):
        section_numbers.add(int(match.group("num")))
    for match in _SDS_NUMERIC_SECTION_RE.finditer(text):
        title = match.group("title").strip().lower()
        if any(token in title for token in _SDS_SECTION_TITLE_TOKENS):
            section_numbers.add(int(match.group("num")))
    return sorted(section_numbers)


def _classify_mismatch(*, expected: bool, actual: bool, text: str) -> str:
    if expected and not actual:
        if not SDS_TITLE_RE.search(text):
            return "missing_sds_title"
        if _NON_SDS_GUIDE_RE.search(text):
            return "rejected_non_sds_guide"
        if _NON_SDS_FACT_SHEET_RE.search(text):
            return "rejected_non_sds_fact_sheet"
        if _NON_SDS_CFR_RE.search(text):
            return "rejected_non_sds_cfr"
        sections = _extract_section_numbers(text=text)
        return f"too_few_sections:{len(sections)}"

    if (not expected) and actual:
        return "false_positive"

    return "mismatch"
