"""Unit tests for textbook integrity validation and pristine build contract.

Purpose:
    Validate PR-0076 fail-closed integrity behavior for textbook corpus promotion.
Relationships:
    - Exercises `scripts.build_textbook_corpus_integrity_gates` public functions.
    - Verifies machine-readable report outputs and pristine build blocking rules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import pytest

from scripts.build_textbook_corpus_integrity_gates import (
    build_pristine_copy,
    run_integrity_validation,
    write_validation_artifacts,
)


class _GateFinding(TypedDict):
    code: str
    severity: str
    line_no: int | None


class _Gate(TypedDict):
    gate: str
    passed: bool
    critical_count: int
    warning_count: int
    metrics: dict[str, int]
    findings: list[_GateFinding]


class _GateReport(TypedDict):
    gates: list[_Gate]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _gate(report: _GateReport, gate_name: str) -> _Gate:
    for gate in report["gates"]:
        if gate.get("gate") == gate_name:
            return gate
    raise AssertionError(f"Gate not found: {gate_name}")


def _valid_markdown() -> str:
    return (
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


def _missing_answer_key_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:1]]\n"
        "## 1 Syror\n"
        "Text.\n\n"
        "[[page:2]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "1.1 Uppgift ett.\n"
        "1.2 Uppgift två.\n"
    )


def _regressing_page_anchor_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:2]]\n"
        "## Kapitel 1\n"
        "Text.\n\n"
        "[[page:1]]\n"
        "## Kapitel 2\n"
        "Mer text.\n\n"
        "[[page:1]]\n"
        "## Kapitel 3\n"
    )


def _ocr_gap_numbering_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:1]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "1.1 Uppgift ett.\n"
        "1.2 Uppgift två.\n"
        "1.4 Uppgift fyra.\n"
        "1.7 Uppgift sju.\n\n"
        "[[page:2]]\n"
        "## SVAR OCH LÖSNINGAR\n"
        "1.1 Svar ett.\n"
        "1.2 Svar två.\n"
        "1.4 Svar fyra.\n"
        "1.7 Svar sju.\n"
    )


def _exercise_section_with_scalar_noise_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:1]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "- 2.19 Uppgift nitton.\n"
        "2. a) Deluppgift som inte ska tolkas som egen övningsrubrik.\n"
        "22,5 cm3 förbrukades i försöket.\n"
        "- 2.20 Uppgift tjugo.\n\n"
        "[[page:2]]\n"
        "## SVAR OCH LÖSNINGAR\n"
        "2.19 Svar nitton.\n"
        "2.20 Svar tjugo.\n"
    )


def _regressing_and_duplicate_exercise_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:1]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "1.1 Uppgift ett.\n"
        "1.3 Uppgift tre.\n"
        "1.3 Dubblett.\n"
        "1.2 Regression.\n\n"
        "[[page:2]]\n"
        "## SVAR OCH LÖSNINGAR\n"
        "1.1 Svar ett.\n"
        "1.2 Svar två.\n"
        "1.3 Svar tre.\n"
    )


def _multiple_answer_heading_blocks_markdown() -> str:
    return (
        "# Syntes\n\n"
        "[[page:1]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "1.1 Uppgift ett.\n"
        "1.2 Uppgift två.\n\n"
        "[[page:2]]\n"
        "## SVAR OCH LÖSNINGAR\n"
        "1.1 Svar ett.\n"
        "1.2 Svar två.\n\n"
        "[[page:3]]\n"
        "## ÖVNINGSUPPGIFTER\n"
        "2.1 Uppgift ett.\n"
        "2.2 Uppgift två.\n\n"
        "[[page:4]]\n"
        "## SVAR OCH LÖSNINGAR\n"
        "2.1 Svar ett.\n"
        "2.2 Svar två.\n"
    )


def _critical_manual_issue(code: str) -> dict[str, Any]:
    return {
        "code": code,
        "line_no": 42,
        "severity": "critical",
        "manual_required": True,
        "line_text": "Corrupted span",
    }


def test_validate_passes_with_ordered_anchors_and_no_critical_unresolved(
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "ordered.md"
    _write_markdown(markdown_path, _valid_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-pass",
    )
    artifacts = write_validation_artifacts(
        output_dir=tmp_path / "validate-pass",
        input_markdown=markdown_path,
        report=bundle.report,
    )

    assert bundle.report["summary"]["all_critical_gates_passed"] is True
    assert Path(artifacts["report_json"]).is_file()
    assert Path(artifacts["findings_jsonl"]).is_file()
    assert Path(artifacts["checklist_md"]).is_file()


def test_validate_fails_when_page_anchors_regress_or_duplicate(tmp_path: Path) -> None:
    markdown_path = tmp_path / "regressing.md"
    _write_markdown(markdown_path, _regressing_page_anchor_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-anchor-fail",
    )

    assert bundle.report["summary"]["all_critical_gates_passed"] is False
    page_gate = _gate(bundle.report, "page_anchor_continuity")
    assert page_gate["critical_count"] > 0
    assert any(
        finding["code"] in {"duplicate_page_anchor", "page_anchor_out_of_order"}
        for finding in page_gate["findings"]
    )


def test_validate_fails_when_manual_queue_has_unresolved_critical_codes(tmp_path: Path) -> None:
    markdown_path = tmp_path / "ordered.md"
    _write_markdown(markdown_path, _valid_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    unresolved_rows = [
        _critical_manual_issue("protected_zone_page_anchor_candidate"),
        _critical_manual_issue("answer_key_mapping_gap"),
    ]
    _write_jsonl(issue_ledger_path, unresolved_rows)
    _write_jsonl(
        manual_queue_path,
        unresolved_rows,
    )

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-critical-fail",
    )

    assert bundle.report["summary"]["all_critical_gates_passed"] is False
    unresolved_gate = _gate(bundle.report, "unresolved_critical_issue_policy")
    assert unresolved_gate["critical_count"] > 0
    assert any(
        finding["code"] == "unresolved_critical_issues_present"
        for finding in unresolved_gate["findings"]
    )


def test_validate_fails_when_answer_key_heading_missing_where_expected(tmp_path: Path) -> None:
    markdown_path = tmp_path / "missing-answer-key.md"
    _write_markdown(markdown_path, _missing_answer_key_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-answer-key-fail",
    )

    assert bundle.report["summary"]["all_critical_gates_passed"] is False
    answer_gate = _gate(bundle.report, "answer_key_heading_consistency")
    assert answer_gate["critical_count"] > 0
    assert any(finding["code"] == "missing_answer_heading" for finding in answer_gate["findings"])


def test_validate_allows_monotonic_ocr_gaps_without_critical_failure(tmp_path: Path) -> None:
    markdown_path = tmp_path / "ocr-gaps.md"
    _write_markdown(markdown_path, _ocr_gap_numbering_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-gap-warning",
    )

    numbering_gate = _gate(bundle.report, "exercise_numbering_continuity")
    assert numbering_gate["critical_count"] == 0
    assert numbering_gate["warning_count"] > 0
    assert any(
        finding["code"] == "exercise_numbering_gap" for finding in numbering_gate["findings"]
    )
    assert bundle.report["summary"]["all_critical_gates_passed"] is True


def test_validate_ignores_scalar_prefixes_inside_exercise_prose(tmp_path: Path) -> None:
    markdown_path = tmp_path / "exercise-scalar-noise.md"
    _write_markdown(markdown_path, _exercise_section_with_scalar_noise_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-scalar-noise",
    )

    numbering_gate = _gate(bundle.report, "exercise_numbering_continuity")
    assert numbering_gate["critical_count"] == 0
    assert numbering_gate["metrics"]["exercise_count"] == 2
    assert bundle.report["summary"]["all_critical_gates_passed"] is True


def test_validate_fails_on_duplicate_or_regressing_exercise_numbering(tmp_path: Path) -> None:
    markdown_path = tmp_path / "exercise-regressions.md"
    _write_markdown(markdown_path, _regressing_and_duplicate_exercise_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-regression-critical",
    )

    numbering_gate = _gate(bundle.report, "exercise_numbering_continuity")
    assert numbering_gate["critical_count"] > 0
    assert any(
        finding["code"] in {"exercise_numbering_duplicate", "exercise_numbering_regression"}
        for finding in numbering_gate["findings"]
    )
    assert bundle.report["summary"]["all_critical_gates_passed"] is False


def test_validate_collects_answer_entries_from_multiple_answer_heading_blocks(
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "multi-answer-blocks.md"
    _write_markdown(markdown_path, _multiple_answer_heading_blocks_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    bundle = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "validate-multi-answer-blocks",
    )

    answer_gate = _gate(bundle.report, "answer_key_heading_consistency")
    assert answer_gate["critical_count"] == 0
    assert answer_gate["metrics"]["answer_heading_count"] == 2
    assert answer_gate["metrics"]["answer_count"] == 4
    assert answer_gate["metrics"]["missing_answer_mappings"] == 0
    assert bundle.report["summary"]["all_critical_gates_passed"] is True


def test_validate_report_fields_and_gate_summary_are_deterministic(tmp_path: Path) -> None:
    markdown_path = tmp_path / "ordered.md"
    _write_markdown(markdown_path, _valid_markdown())
    issue_ledger_path = tmp_path / "issue-ledger.jsonl"
    manual_queue_path = tmp_path / "manual-queue.jsonl"
    _write_jsonl(issue_ledger_path, [])
    _write_jsonl(manual_queue_path, [])

    run_one = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "deterministic-one",
    )
    run_two = run_integrity_validation(
        input_markdown=markdown_path,
        issue_ledger=issue_ledger_path,
        manual_queue=manual_queue_path,
        output_dir=tmp_path / "deterministic-two",
    )

    def _canonical(report: dict[str, Any]) -> dict[str, Any]:
        return {
            "summary": report["summary"],
            "gates": [
                {
                    "gate": gate["gate"],
                    "passed": gate["passed"],
                    "critical_count": gate["critical_count"],
                    "warning_count": gate["warning_count"],
                    "metrics": gate["metrics"],
                    "findings": [
                        {
                            "code": finding["code"],
                            "severity": finding["severity"],
                            "line_no": finding["line_no"],
                        }
                        for finding in gate["findings"]
                    ],
                }
                for gate in report["gates"]
            ],
        }

    assert _canonical(run_one.report) == _canonical(run_two.report)


def test_build_pristine_succeeds_only_when_validate_passes_if_exposed(tmp_path: Path) -> None:
    failing_markdown = tmp_path / "failing.md"
    _write_markdown(failing_markdown, _missing_answer_key_markdown())
    failing_issue_ledger = tmp_path / "failing-issue-ledger.jsonl"
    failing_queue = tmp_path / "failing-manual-queue.jsonl"
    _write_jsonl(failing_issue_ledger, [])
    _write_jsonl(failing_queue, [])
    failing_validation = run_integrity_validation(
        input_markdown=failing_markdown,
        issue_ledger=failing_issue_ledger,
        manual_queue=failing_queue,
        output_dir=tmp_path / "build-precheck-fail",
    )
    assert failing_validation.report["summary"]["all_critical_gates_passed"] is False

    with pytest.raises(SystemExit):
        build_pristine_copy(
            input_markdown=failing_markdown,
            report=failing_validation.report,
            output_dir=tmp_path / "failing-pristine",
        )

    passing_markdown = tmp_path / "passing.md"
    _write_markdown(passing_markdown, _valid_markdown())
    passing_issue_ledger = tmp_path / "passing-issue-ledger.jsonl"
    passing_queue = tmp_path / "passing-manual-queue.jsonl"
    _write_jsonl(passing_issue_ledger, [])
    _write_jsonl(passing_queue, [])
    passing_validation = run_integrity_validation(
        input_markdown=passing_markdown,
        issue_ledger=passing_issue_ledger,
        manual_queue=passing_queue,
        output_dir=tmp_path / "build-precheck-pass",
    )
    assert passing_validation.report["summary"]["all_critical_gates_passed"] is True

    result = build_pristine_copy(
        input_markdown=passing_markdown,
        report=passing_validation.report,
        output_dir=tmp_path / "passing-pristine",
    )
    pristine_md = Path(result["pristine_markdown"])
    pristine_report = Path(result["pristine_report"])
    assert pristine_md.is_file()
    assert pristine_report.is_file()
