"""Unit tests for stored-report reading and issue-row parsing in textbook integrity gates.

Purpose:
    Check that stored integrity reports and on-disk issue rows are parsed with the
    same defaults and failures the pristine build and the issue-policy gate always had.
Relationships:
    - Exercises `scripts.build_textbook_corpus_integrity_gates` public functions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import JsonValue

from scripts.build_textbook_corpus_integrity_gates import (
    IntegrityGateRow,
    IntegrityReport,
    build_pristine_copy,
    run_integrity_validation,
)

_VALID_MARKDOWN = (
    "# Syntes\n\n"
    "[[page:1]]\n"
    "## 1 Syror\n"
    "Text.\n\n"
    "[[page:2]]\n"
    "## ÖVNINGSUPPGIFTER\n"
    "1.1 Uppgift ett.\n"
    "1.2 Uppgift två.\n\n"
    "[[page:3]]\n"
    "## SVAR OCH LÖSNINGAR\n"
    "1.1 Svar ett.\n"
    "1.2 Svar två.\n"
)


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, JsonValue]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _valid_markdown() -> str:
    return _VALID_MARKDOWN


def _gate(report: IntegrityReport, gate_name: str) -> IntegrityGateRow:
    for gate in report["gates"]:
        if gate["gate"] == gate_name:
            return gate
    raise AssertionError(f"Gate not found: {gate_name}")


def test_build_pristine_reads_stored_report_file_and_writes_checklist(tmp_path: Path) -> None:
    markdown_path = tmp_path / "stored.md"
    _write_markdown(markdown_path, _valid_markdown())
    ledger_path = tmp_path / "ledger.jsonl"
    queue_path = tmp_path / "queue.jsonl"
    _write_jsonl(ledger_path, [])
    _write_jsonl(queue_path, [])
    validation = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=ledger_path,
        manual_queue=queue_path,
        output_dir=tmp_path / "stored-validate",
    )
    stored_report = tmp_path / "stored-report.json"
    stored_report.write_text(json.dumps(validation.report), encoding="utf-8")
    checklist = tmp_path / "stored-checklist.md"

    result = build_pristine_copy(
        input_markdown=markdown_path,
        validation_report_path=stored_report,
        output_dir=tmp_path / "stored-pristine",
        checklist_path=checklist,
    )

    assert Path(result["pristine_markdown"]).is_file()
    checklist_lines = checklist.read_text(encoding="utf-8").splitlines()
    assert "- All critical gates passed: `True`" in checklist_lines
    first_gate = validation.report["gates"][0]
    assert (
        f"- `{first_gate['gate']}`: passed={first_gate['passed']} "
        f"critical={first_gate['critical_count']} warning={first_gate['warning_count']}"
    ) in checklist_lines


def test_build_pristine_blocks_when_stored_report_has_no_passing_summary(tmp_path: Path) -> None:
    markdown_path = tmp_path / "blocked.md"
    _write_markdown(markdown_path, _valid_markdown())
    stored_report = tmp_path / "blocked-report.json"
    stored_report.write_text(json.dumps({"summary": "oops", "gates": "nope"}), encoding="utf-8")

    with pytest.raises(SystemExit, match="Pristine build blocked"):
        build_pristine_copy(
            input_markdown=markdown_path,
            validation_report_path=stored_report,
            output_dir=tmp_path / "blocked-pristine",
        )


def test_issue_policy_coerces_ledger_and_queue_rows_read_from_disk(tmp_path: Path) -> None:
    markdown_path = tmp_path / "rows.md"
    _write_markdown(markdown_path, _valid_markdown())
    ledger_path = tmp_path / "rows-ledger.jsonl"
    queue_path = tmp_path / "rows-queue.jsonl"
    # status is absent (reads as unresolved) and line_no is not an int (reads as 0).
    row: dict[str, JsonValue] = {
        "code": "x_issue",
        "severity": "HIGH",
        "manual_required": 1,
        "line_no": "7",
    }
    _write_jsonl(ledger_path, [row])
    _write_jsonl(queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=ledger_path,
        manual_queue=queue_path,
        output_dir=tmp_path / "rows-out",
    )

    gate = _gate(bundle.report, "unresolved_critical_issue_policy")
    assert [finding["code"] for finding in gate["findings"]] == [
        "critical_issue_missing_from_manual_queue"
    ]
    assert "('x_issue', 0)" in gate["findings"][0]["message"]
