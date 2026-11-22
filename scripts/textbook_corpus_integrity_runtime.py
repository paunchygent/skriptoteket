"""Runtime APIs for textbook corpus integrity validation and pristine build gating.

Purpose:
    Implement deterministic integrity validation gates and fail-closed pristine build
    promotion for textbook corpus artifacts.

Relationships:
    - Uses pure gate evaluators from `scripts.textbook_corpus_integrity_gates_core`.
    - Uses shared models/constants from `scripts.textbook_corpus_integrity_models`.
    - Re-exported by `scripts.build_textbook_corpus_integrity_gates`.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict

from pydantic import JsonValue

from scripts.textbook_corpus_integrity_gates_core import (
    IssueRow,
    build_gate_results,
    parse_issue_row,
)
from scripts.textbook_corpus_integrity_models import DEFAULT_OUTPUT_DIR


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


class IntegrityReportView(TypedDict, total=False):
    """Report-shaped mapping read defensively by pristine-build/checklist paths.

    The loaded or caller-supplied report keeps ``JsonValue`` fields so the
    readers' own ``isinstance`` checks degrade malformed content exactly like
    the untyped ``dict.get`` reads did.
    """

    generated_at: JsonValue
    summary: JsonValue
    gates: JsonValue


@dataclass(frozen=True, slots=True)
class ValidationBundle:
    """Compatibility envelope for validation/build caller contracts."""

    report: IntegrityReport
    all_critical_gates_passed: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--input-markdown", type=Path, required=True)
    validate.add_argument("--issue-ledger", type=Path, default=None)
    validate.add_argument("--manual-queue", type=Path, required=True)
    validate.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    validate.add_argument("--report-path", type=Path, default=None)
    validate.add_argument("--checklist-path", type=Path, default=None)

    build_pristine_parser = subparsers.add_parser("build-pristine")
    build_pristine_parser.add_argument("--input-markdown", type=Path, required=True)
    build_pristine_parser.add_argument("--issue-ledger", type=Path, default=None)
    build_pristine_parser.add_argument("--manual-queue", type=Path, required=True)
    build_pristine_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    build_pristine_parser.add_argument("--report-path", type=Path, default=None)
    build_pristine_parser.add_argument("--checklist-path", type=Path, default=None)
    build_pristine_parser.add_argument("--output-markdown", type=Path, default=None)

    return parser.parse_args()


def _read_jsonl(path: Path) -> list[IssueRow]:
    if not path.exists():
        return []
    rows: list[IssueRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed: JsonValue = json.loads(stripped)
        row = parse_issue_row(parsed)
        if row is not None:
            rows.append(row)
    return rows


def _write_json(path: Path, payload: IntegrityReport | PristineBuildReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, JsonValue]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _int_or_zero(value: JsonValue) -> int:
    candidate = value or 0
    if isinstance(candidate, (dict, list)):
        raise TypeError(
            f"int() argument must be a string or a real number, not {type(candidate).__name__!r}"
        )
    return int(candidate)


def _parse_report_view(value: JsonValue) -> IntegrityReportView | None:
    """Build the defensively-read report view; non-objects yield ``None``.

    Returning ``None`` preserves the old ``isinstance(parsed, dict)`` gate so a
    non-object payload still falls back to a fresh validation run.
    """
    if not isinstance(value, dict):
        return None
    view = IntegrityReportView()
    if "generated_at" in value:
        view["generated_at"] = value["generated_at"]
    if "summary" in value:
        view["summary"] = value["summary"]
    if "gates" in value:
        view["gates"] = value["gates"]
    return view


def _resolve_input_path(
    *,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
) -> Path:
    candidate = input_markdown or restored_markdown or markdown_path
    if candidate is None:
        raise SystemExit("Missing markdown input path.")
    return candidate.resolve()


def _resolve_manual_queue_path(
    *,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
) -> Path:
    candidate = manual_queue_path or manual_queue or unresolved_manual_queue_path
    if candidate is None:
        raise SystemExit("Missing manual queue path.")
    return candidate.resolve()


def _resolve_issue_ledger_path(
    *,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
) -> Path | None:
    candidate = issue_ledger_path or issue_ledger
    if candidate is None:
        return None
    return candidate.resolve()


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


def _write_checklist(
    path: Path,
    *,
    report: IntegrityReport | IntegrityReportView,
    input_markdown: Path,
) -> None:
    summary = report.get("summary")
    summary_obj = summary if isinstance(summary, dict) else {}
    gate_rows = report.get("gates")
    gates = gate_rows if isinstance(gate_rows, list) else []
    lines = [
        "# Textbook Corpus Integrity Checklist",
        "",
        f"- Input markdown: `{input_markdown}`",
        f"- Generated at: `{report.get('generated_at', '')}`",
        f"- All critical gates passed: `{summary_obj.get('all_critical_gates_passed', False)}`",
        "",
        "## Gate Results",
        "",
    ]
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        lines.append(
            "- "
            f"`{gate.get('gate', 'unknown')}`: passed={gate.get('passed')} "
            f"critical={gate.get('critical_count', 0)} "
            f"warning={gate.get('warning_count', 0)}"
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

    flattened_findings: list[dict[str, JsonValue]] = []
    gate_rows = report.get("gates")
    if isinstance(gate_rows, list):
        for gate_row in gate_rows:
            if not isinstance(gate_row, dict):
                continue
            gate_code = str(gate_row.get("gate") or "unknown")
            findings = gate_row.get("findings")
            if not isinstance(findings, list):
                continue
            for finding in findings:
                if not isinstance(finding, dict):
                    continue
                row: dict[str, JsonValue] = {
                    "code": finding["code"],
                    "severity": finding["severity"],
                    "line_no": finding["line_no"],
                    "message": finding["message"],
                    "gate": gate_code,
                }
                flattened_findings.append(row)

    flattened_findings.sort(
        key=lambda row: (
            _int_or_zero(row.get("line_no")),
            str(row.get("gate") or ""),
            str(row.get("code") or ""),
        )
    )

    _write_json(resolved_report, report)
    _write_jsonl(findings_path, flattened_findings)
    _write_checklist(resolved_checklist, report=report, input_markdown=input_markdown)
    return {
        "report_json": str(resolved_report),
        "findings_jsonl": str(findings_path),
        "checklist_md": str(resolved_checklist),
    }


def validate_integrity_gates(
    *,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
    report_path: Path | None = None,
    checklist_path: Path | None = None,
    output_dir: Path | None = None,
) -> IntegrityReport:
    """Run integrity validators and write report/checklist artifacts."""
    resolved_input = _resolve_input_path(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
    )
    resolved_manual_queue = _resolve_manual_queue_path(
        manual_queue_path=manual_queue_path,
        manual_queue=manual_queue,
        unresolved_manual_queue_path=unresolved_manual_queue_path,
    )
    resolved_issue_ledger = _resolve_issue_ledger_path(
        issue_ledger_path=issue_ledger_path,
        issue_ledger=issue_ledger,
    )
    resolved_output_dir = (output_dir or DEFAULT_OUTPUT_DIR).resolve()

    lines = resolved_input.read_text(encoding="utf-8").splitlines()
    manual_rows = _read_jsonl(resolved_manual_queue)
    issue_ledger_rows = _read_jsonl(resolved_issue_ledger) if resolved_issue_ledger else []

    gate_results = build_gate_results(
        lines=lines,
        manual_queue=manual_rows,
        issue_ledger=issue_ledger_rows,
    )
    all_critical_gates_passed = all(gate.passed for gate in gate_results)

    report = IntegrityReport(
        generated_at=datetime.now(UTC).isoformat(),
        input_markdown=str(resolved_input),
        manual_queue_path=str(resolved_manual_queue),
        issue_ledger_path=str(resolved_issue_ledger) if resolved_issue_ledger else None,
        passed=all_critical_gates_passed,
        summary=IntegritySummary(
            all_critical_gates_passed=all_critical_gates_passed,
            gate_count=len(gate_results),
            critical_findings_total=sum(gate.critical_count for gate in gate_results),
            warning_findings_total=sum(gate.warning_count for gate in gate_results),
        ),
        gate_summary=IntegrityGateSummary(
            all_passed=all_critical_gates_passed,
            failed_gates=sum(1 for gate in gate_results if not gate.passed),
            passed_gates=sum(1 for gate in gate_results if gate.passed),
        ),
        failed_gates=[gate.gate for gate in gate_results if not gate.passed],
        gates=[
            IntegrityGateRow(
                gate=gate.gate,
                passed=gate.passed,
                critical_count=gate.critical_count,
                warning_count=gate.warning_count,
                metrics=gate.metrics,
                findings=[
                    IntegrityFinding(
                        code=finding.code,
                        severity=finding.severity,
                        line_no=finding.line_no,
                        message=finding.message,
                    )
                    for finding in gate.findings
                ],
            )
            for gate in gate_results
        ],
    )
    artifact_paths = write_validation_artifacts(
        output_dir=resolved_output_dir,
        input_markdown=resolved_input,
        report=report,
        report_path=report_path,
        checklist_path=checklist_path,
    )
    report["artifact_paths"] = artifact_paths
    if report_path is not None:
        _write_json(report_path.resolve(), report)
    return report


def run_integrity_gates(
    *,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
    report_path: Path | None = None,
    checklist_path: Path | None = None,
    output_dir: Path | None = None,
) -> IntegrityReport:
    """Compatibility alias for validation entrypoint."""
    return validate_integrity_gates(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
        manual_queue_path=manual_queue_path,
        manual_queue=manual_queue,
        unresolved_manual_queue_path=unresolved_manual_queue_path,
        issue_ledger_path=issue_ledger_path,
        issue_ledger=issue_ledger,
        report_path=report_path,
        checklist_path=checklist_path,
        output_dir=output_dir,
    )


def run_integrity_validation(
    *,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
    report_path: Path | None = None,
    checklist_path: Path | None = None,
    output_dir: Path | None = None,
) -> ValidationBundle:
    """Compatibility wrapper used by callers expecting a structured bundle."""
    report = validate_integrity_gates(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
        manual_queue_path=manual_queue_path,
        manual_queue=manual_queue,
        unresolved_manual_queue_path=unresolved_manual_queue_path,
        issue_ledger_path=issue_ledger_path,
        issue_ledger=issue_ledger,
        report_path=report_path,
        checklist_path=checklist_path,
        output_dir=output_dir,
    )
    summary = report.get("summary")
    summary_obj = summary if isinstance(summary, dict) else {}
    return ValidationBundle(
        report=report,
        all_critical_gates_passed=bool(summary_obj.get("all_critical_gates_passed")),
    )


def build_pristine(
    *,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
    validation_report_path: Path | None = None,
    validation_report: IntegrityReport | IntegrityReportView | None = None,
    output_markdown: Path | None = None,
    pristine_markdown_path: Path | None = None,
    pristine_path: Path | None = None,
    report_path: Path | None = None,
    checklist_path: Path | None = None,
    output_dir: Path | None = None,
) -> PristineBuildReport:
    """Build pristine markdown copy only when integrity gates pass."""
    resolved_input = _resolve_input_path(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
    )
    resolved_output_dir = (output_dir or DEFAULT_OUTPUT_DIR).resolve()

    report: IntegrityReport | IntegrityReportView | None = validation_report
    if report is None and validation_report_path is not None and validation_report_path.exists():
        parsed: JsonValue = json.loads(validation_report_path.read_text(encoding="utf-8"))
        report = _parse_report_view(parsed)
    if report is None:
        report = validate_integrity_gates(
            input_markdown=resolved_input,
            manual_queue_path=_resolve_manual_queue_path(
                manual_queue_path=manual_queue_path,
                manual_queue=manual_queue,
                unresolved_manual_queue_path=unresolved_manual_queue_path,
            ),
            issue_ledger_path=_resolve_issue_ledger_path(
                issue_ledger_path=issue_ledger_path,
                issue_ledger=issue_ledger,
            ),
            output_dir=resolved_output_dir,
            report_path=report_path,
            checklist_path=checklist_path,
        )

    summary = report.get("summary")
    summary_obj = summary if isinstance(summary, dict) else {}
    if not bool(summary_obj.get("all_critical_gates_passed")):
        raise SystemExit("Pristine build blocked: integrity gates failed.")

    pristine_output_path = (
        output_markdown
        or pristine_markdown_path
        or pristine_path
        or (resolved_output_dir / "pristine" / f"{resolved_input.stem}.pristine.md")
    ).resolve()
    pristine_output_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_text = resolved_input.read_text(encoding="utf-8")
    pristine_output_path.write_text(markdown_text, encoding="utf-8")

    build_report_path = (
        report_path
        or resolved_output_dir / "pristine" / f"{resolved_input.stem}.pristine-report.json"
    ).resolve()
    build_report = PristineBuildReport(
        generated_at=datetime.now(UTC).isoformat(),
        passed=True,
        summary=PristineBuildSummary(
            all_critical_gates_passed=True,
            all_passed=True,
        ),
        input_markdown=str(resolved_input),
        pristine_markdown=str(pristine_output_path),
    )
    _write_json(build_report_path, build_report)
    if checklist_path is not None:
        _write_checklist(checklist_path.resolve(), report=report, input_markdown=resolved_input)
    return build_report


def build_pristine_copy(
    *,
    output_dir: Path | None = None,
    input_markdown: Path | None = None,
    restored_markdown: Path | None = None,
    markdown_path: Path | None = None,
    manual_queue_path: Path | None = None,
    manual_queue: Path | None = None,
    unresolved_manual_queue_path: Path | None = None,
    issue_ledger_path: Path | None = None,
    issue_ledger: Path | None = None,
    validation_report_path: Path | None = None,
    validation_report: IntegrityReport | IntegrityReportView | None = None,
    report: IntegrityReport | IntegrityReportView | None = None,
    output_markdown: Path | None = None,
    pristine_markdown_path: Path | None = None,
    pristine_path: Path | None = None,
    checklist_path: Path | None = None,
) -> PristineBuildReport:
    """Compatibility wrapper that includes pristine report output path."""
    resolved_output_dir = (output_dir or DEFAULT_OUTPUT_DIR).resolve()
    resolved_input = _resolve_input_path(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
    )
    resolved_report_path = (
        resolved_output_dir / "pristine" / f"{resolved_input.stem}.pristine-report.json"
    ).resolve()

    effective_report = validation_report or report
    build_report = build_pristine(
        input_markdown=input_markdown,
        restored_markdown=restored_markdown,
        markdown_path=markdown_path,
        manual_queue_path=manual_queue_path,
        manual_queue=manual_queue,
        unresolved_manual_queue_path=unresolved_manual_queue_path,
        issue_ledger_path=issue_ledger_path,
        issue_ledger=issue_ledger,
        validation_report_path=validation_report_path,
        validation_report=effective_report,
        output_markdown=output_markdown,
        pristine_markdown_path=pristine_markdown_path,
        pristine_path=pristine_path,
        output_dir=resolved_output_dir,
        report_path=resolved_report_path,
        checklist_path=checklist_path,
    )
    return PristineBuildReport(
        generated_at=build_report["generated_at"],
        passed=build_report["passed"],
        summary=build_report["summary"],
        input_markdown=build_report["input_markdown"],
        pristine_markdown=build_report["pristine_markdown"],
        pristine_report=str(resolved_report_path),
    )


def main() -> None:
    args = _parse_args()

    if args.command == "validate":
        report = validate_integrity_gates(
            input_markdown=args.input_markdown.resolve(),
            manual_queue_path=args.manual_queue.resolve(),
            issue_ledger_path=args.issue_ledger.resolve() if args.issue_ledger else None,
            output_dir=args.output_dir.resolve(),
            report_path=args.report_path.resolve() if args.report_path else None,
            checklist_path=args.checklist_path.resolve() if args.checklist_path else None,
        )
        summary = report.get("summary")
        summary_obj = summary if isinstance(summary, dict) else {}
        print(
            "[textbook_integrity_gates] "
            f"all_critical_gates_passed={summary_obj.get('all_critical_gates_passed')} "
            f"critical_findings_total={summary_obj.get('critical_findings_total')}"
        )
        if not bool(summary_obj.get("all_critical_gates_passed")):
            raise SystemExit(1)
        return

    if args.command == "build-pristine":
        report = build_pristine(
            input_markdown=args.input_markdown.resolve(),
            manual_queue_path=args.manual_queue.resolve(),
            issue_ledger_path=args.issue_ledger.resolve() if args.issue_ledger else None,
            output_markdown=args.output_markdown.resolve() if args.output_markdown else None,
            output_dir=args.output_dir.resolve(),
            report_path=args.report_path.resolve() if args.report_path else None,
            checklist_path=args.checklist_path.resolve() if args.checklist_path else None,
        )
        print(
            "[textbook_integrity_gates] "
            f"pristine_built={report.get('pristine_markdown')} passed={report.get('passed')}"
        )
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
