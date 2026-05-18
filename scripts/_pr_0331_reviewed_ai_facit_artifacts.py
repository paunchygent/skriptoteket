"""Reviewed AI-facit artifact inspection helpers.

Domain purpose:
    Validate downloaded Exam Converter artifacts against the PR-0331 reviewed
    answer-key contract without coupling the browser proof script to PDF and
    QTI parsing details.

Relationships:
    - Supports `scripts/playwright_pr_0331_reviewed_ai_facit_live.py`.
    - Checks Sir Convert produced `effective_ir_json`, PDF, and QTI artifacts.
    - Keeps forbidden producer diagnostics out of teacher-facing export proof.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect
from pypdf import PdfReader

FORBIDDEN_ARTIFACT_TEXT = (
    "Manuell bedömning. Ursprunglig lucktext utan betrodda accepterade värden.",
    "Ursprunglig lucktext utan betrodda accepterade värden",
    "unsupported_target_shape",
    "qti_package_export_disabled",
    "Orsak:",
)


def extract_effective_keys(effective_ir: Any) -> list[dict[str, Any]]:
    if not isinstance(effective_ir, dict):
        return []
    rows: list[dict[str, Any]] = []
    items = effective_ir.get("items")
    if not isinstance(items, list):
        return rows
    for item in items:
        if not isinstance(item, dict):
            continue
        key = item.get("effective_answer_key")
        if not isinstance(key, dict):
            continue
        rows.append(
            {
                "item_id": item.get("item_id"),
                "item_type": item.get("item_type"),
                "kind": key.get("kind"),
                "provenance": key.get("provenance"),
                "lineage_present": isinstance(key.get("lineage"), dict),
                "correct_alternative_ids": key.get("correct_alternative_ids"),
                "correct_gap_answers": key.get("correct_gap_answers"),
            }
        )
    return rows


def download_file(page: Page, *, artifact_key: str, artifact_dir: Path) -> Path:
    button = page.locator(f'[data-test="exam-converter-download-file-{artifact_key}"]').first
    expect(button).to_be_enabled(timeout=30_000)
    with page.expect_download() as download_info:
        button.click()
    download = download_info.value
    output_path = artifact_dir / (download.suggested_filename or f"{artifact_key}.bin")
    download.save_as(str(output_path))
    return output_path


def inspect_pdf(path: Path, effective_keys: list[dict[str, Any]]) -> dict[str, Any]:
    reader = PdfReader(str(path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    gap_values = [
        str(value)
        for key in effective_keys
        for gap in key.get("correct_gap_answers") or []
        if isinstance(gap, dict)
        for value in gap.get("accepted_values") or []
    ]
    return {
        "path": str(path),
        "page_count": len(reader.pages),
        "forbidden_text_hits": [value for value in FORBIDDEN_ARTIFACT_TEXT if value in text],
        "gap_value_hits": sorted({value for value in gap_values if value and value in text}),
        "gap_value_count": len(gap_values),
    }


def inspect_qti(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        xml_names = [name for name in archive.namelist() if name.endswith(".xml")]
        xml_payloads = {
            name: archive.read(name).decode("utf-8", errors="replace") for name in xml_names
        }
    joined = "\n".join(xml_payloads.values())
    return {
        "path": str(path),
        "xml_file_count": len(xml_names),
        "correct_response_count": joined.count("<correctResponse>"),
        "forbidden_text_hits": [value for value in FORBIDDEN_ARTIFACT_TEXT if value in joined],
    }


def assert_artifact_integrity(summary: dict[str, Any]) -> None:
    findings: list[str] = []
    effective_keys = summary["effective_key_summary"]
    if not effective_keys:
        findings.append("reviewed apply did not expose effective answer keys")
    if summary["pdf_inspection"]["forbidden_text_hits"]:
        findings.append("PDF exposes forbidden internal fallback diagnostics")
    if summary["qti_inspection"]["forbidden_text_hits"]:
        findings.append("QTI exposes forbidden internal fallback diagnostics")
    if summary["qti_inspection"]["correct_response_count"] == 0 and effective_keys:
        findings.append("QTI contains no correctResponse entries despite effective answer keys")
    if (
        summary["pdf_inspection"]["gap_value_count"] > 0
        and not summary["pdf_inspection"]["gap_value_hits"]
    ):
        findings.append("PDF contains no accepted gapped key values")
    summary["upstream_contract_findings"] = findings
    if findings:
        raise AssertionError("; ".join(findings))
