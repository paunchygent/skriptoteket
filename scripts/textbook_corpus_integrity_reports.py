"""Report types, report parsing and artifact writers for textbook corpus integrity gates.

Purpose:
    Define the serialized integrity and pristine-build report shapes, parse a stored
    report into the view the checklist and pristine build read, and write the
    machine-readable and human-readable validation artifacts.

Relationships:
    - Imported by `scripts.textbook_corpus_integrity_runtime`.
    - Re-exported through `scripts.build_textbook_corpus_integrity_gates`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import NotRequired, TypedDict

from pydantic import JsonValue


class IntegrityFinding(TypedDict):
    """One gate finding serialized into an integrity report."""

    code: str
    severity: str
    line_no: int | None
    message: str


class IntegrityGateRow(TypedDict):
    """One gate result serialized into an integrity report."""

    gate: str
    passed: bool
    critical_count: int
    warning_count: int
    metrics: dict[str, int]
    findings: list[IntegrityFinding]


class IntegritySummary(TypedDict):
    """Aggregate gate counters in an integrity report."""

    all_critical_gates_passed: bool
    gate_count: int
    critical_findings_total: int
    warning_findings_total: int


class IntegrityGateSummary(TypedDict):
    """Pass/fail gate counters in an integrity report."""

    all_passed: bool
    failed_gates: int
    passed_gates: int


class IntegrityReport(TypedDict):
    """Machine-readable integrity report written by `validate_integrity_gates`."""

    generated_at: str
    input_markdown: str
    manual_queue_path: str
    issue_ledger_path: str | None
    passed: bool
    summary: IntegritySummary
    gate_summary: IntegrityGateSummary
    failed_gates: list[str]
    gates: list[IntegrityGateRow]
    artifact_paths: NotRequired[dict[str, str]]


class PristineBuildSummary(TypedDict):
    """Summary counters in a pristine build report."""

    all_critical_gates_passed: bool
    all_passed: bool


class PristineBuildReport(TypedDict):
    """Machine-readable report written by `build_pristine`."""

    generated_at: str
    passed: bool
    summary: PristineBuildSummary
    input_markdown: str
    pristine_markdown: str
    pristine_report: NotRequired[str]


class FlattenedFinding(TypedDict):
    """One finding row of the findings JSONL, tagged with its gate."""

    code: str
    severity: str
    line_no: int | None
    message: str
    gate: str


class ChecklistGate(TypedDict):
    """One gate line of the checklist; leaves hold the text the checklist prints."""

    gate: str
    passed: str
    critical_count: str
    warning_count: str


class IntegrityReportView(TypedDict):
    """The fields of a stored or fresh report that the checklist and pristine build read.

    ``all_critical_gates_passed`` drives the pristine-build gate; the ``_text``
    field and the ``ChecklistGate`` leaves hold what the checklist prints.
    """

    generated_at: str
    all_critical_gates_passed: bool
    all_critical_gates_passed_text: str
    gates: list[ChecklistGate]


def parse_report_view(value: JsonValue) -> IntegrityReportView | None:
    """Parse a stored report into the view the checklist reads; non-objects yield ``None``.

    A non-object ``summary`` reads as empty (gate not passed) and a non-list
    ``gates`` as no gates, with non-object gate entries skipped. Printed leaves
    keep their missing-value defaults: ``generated_at`` ``""``, the pass flag
    ``False``, ``gate`` ``"unknown"`` and the counts ``0``.
    """
    if not isinstance(value, dict):
        return None
    summary = value.get("summary")
    summary_obj = summary if isinstance(summary, dict) else {}
    gate_rows = value.get("gates")
    gates: list[ChecklistGate] = []
    for gate in gate_rows if isinstance(gate_rows, list) else []:
        if not isinstance(gate, dict):
            continue
        gates.append(
            ChecklistGate(
                gate=str(gate.get("gate", "unknown")),
                passed=str(gate.get("passed")),
                critical_count=str(gate.get("critical_count", 0)),
                warning_count=str(gate.get("warning_count", 0)),
            )
        )
    return IntegrityReportView(
        generated_at=str(value.get("generated_at", "")),
        all_critical_gates_passed=bool(summary_obj.get("all_critical_gates_passed")),
        all_critical_gates_passed_text=str(summary_obj.get("all_critical_gates_passed", False)),
        gates=gates,
    )


def report_view(report: IntegrityReport) -> IntegrityReportView:
    """Build the checklist view of a freshly built report."""
    passed = report["summary"]["all_critical_gates_passed"]
    return IntegrityReportView(
        generated_at=report["generated_at"],
        all_critical_gates_passed=passed,
        all_critical_gates_passed_text=str(passed),
        gates=[
            ChecklistGate(
                gate=gate["gate"],
                passed=str(gate["passed"]),
                critical_count=str(gate["critical_count"]),
                warning_count=str(gate["warning_count"]),
            )
            for gate in report["gates"]
        ],
    )


def write_json(path: Path, payload: IntegrityReport | PristineBuildReport) -> None:
    """Write a report as sorted, indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[FlattenedFinding]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _report_paths(
    *,
    input_markdown: Path,
    output_dir: Path,
    report_path: Path | None,
    checklist_path: Path | None,
) -> tuple[Path, Path, Path]:
    reports_dir = output_dir / "reports"
    stem = input_markdown.stem
    resolved_report = report_path or reports_dir / f"{stem}.integrity-report.json"
    resolved_checklist = checklist_path or reports_dir / f"{stem}.integrity-checklist.md"
    findings_path = reports_dir / f"{stem}.integrity-findings.jsonl"
    return resolved_report.resolve(), resolved_checklist.resolve(), findings_path.resolve()


def write_checklist(path: Path, *, report: IntegrityReportView, input_markdown: Path) -> None:
    """Write the human-readable gate checklist."""
    lines = [
        "# Textbook Corpus Integrity Checklist",
        "",
        f"- Input markdown: `{input_markdown}`",
        f"- Generated at: `{report['generated_at']}`",
        f"- All critical gates passed: `{report['all_critical_gates_passed_text']}`",
        "",
        "## Gate Results",
        "",
    ]
    for gate in report["gates"]:
        lines.append(
            "- "
            f"`{gate['gate']}`: passed={gate['passed']} "
            f"critical={gate['critical_count']} "
            f"warning={gate['warning_count']}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_validation_artifacts(
    *,
    output_dir: Path,
    input_markdown: Path,
    report: IntegrityReport,
    report_path: Path | None = None,
    checklist_path: Path | None = None,
) -> dict[str, str]:
    """Write machine-readable and human-readable validation artifacts."""
    resolved_report, resolved_checklist, findings_path = _report_paths(
        input_markdown=input_markdown,
        output_dir=output_dir,
        report_path=report_path,
        checklist_path=checklist_path,
    )

    flattened_findings = [
        FlattenedFinding(
            code=finding["code"],
            severity=finding["severity"],
            line_no=finding["line_no"],
            message=finding["message"],
            gate=gate_row["gate"] or "unknown",
        )
        for gate_row in report["gates"]
        for finding in gate_row["findings"]
    ]
    flattened_findings.sort(key=lambda row: (row["line_no"] or 0, row["gate"], row["code"]))

    write_json(resolved_report, report)
    _write_jsonl(findings_path, flattened_findings)
    write_checklist(resolved_checklist, report=report_view(report), input_markdown=input_markdown)
    return {
        "report_json": str(resolved_report),
        "findings_jsonl": str(findings_path),
        "checklist_md": str(resolved_checklist),
    }
