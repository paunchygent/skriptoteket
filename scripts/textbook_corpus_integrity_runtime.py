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
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import JsonValue

from scripts.textbook_corpus_integrity_gates_core import (
    IssueRow,
    build_gate_results,
    parse_issue_row,
)
from scripts.textbook_corpus_integrity_models import DEFAULT_OUTPUT_DIR
from scripts.textbook_corpus_integrity_reports import (
    IntegrityFinding,
    IntegrityGateRow,
    IntegrityGateSummary,
    IntegrityReport,
    IntegrityReportView,
    IntegritySummary,
    PristineBuildReport,
    PristineBuildSummary,
    parse_report_view,
    report_view,
    write_checklist,
    write_json,
    write_validation_artifacts,
)


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
        write_json(report_path.resolve(), report)
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
    return ValidationBundle(
        report=report,
        all_critical_gates_passed=report["summary"]["all_critical_gates_passed"],
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
    validation_report: IntegrityReport | None = None,
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

    report: IntegrityReportView | None = (
        report_view(validation_report) if validation_report is not None else None
    )
    if report is None and validation_report_path is not None and validation_report_path.exists():
        parsed: JsonValue = json.loads(validation_report_path.read_text(encoding="utf-8"))
        report = parse_report_view(parsed)
    if report is None:
        fresh_report = validate_integrity_gates(
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
        report = report_view(fresh_report)

    if not report["all_critical_gates_passed"]:
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
    write_json(build_report_path, build_report)
    if checklist_path is not None:
        write_checklist(checklist_path.resolve(), report=report, input_markdown=resolved_input)
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
    validation_report: IntegrityReport | None = None,
    report: IntegrityReport | None = None,
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
        summary = report["summary"]
        print(
            "[textbook_integrity_gates] "
            f"all_critical_gates_passed={summary['all_critical_gates_passed']} "
            f"critical_findings_total={summary['critical_findings_total']}"
        )
        if not summary["all_critical_gates_passed"]:
            raise SystemExit(1)
        return

    if args.command == "build-pristine":
        build_report = build_pristine(
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
            f"pristine_built={build_report['pristine_markdown']} passed={build_report['passed']}"
        )
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
