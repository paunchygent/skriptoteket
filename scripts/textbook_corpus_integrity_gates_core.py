"""Pure gate evaluators for textbook corpus integrity validation.

Purpose:
    Evaluate deterministic integrity gates from markdown lines and issue rows.

Relationships:
    - Imported by `scripts.textbook_corpus_integrity_runtime`.
    - Uses shared models/constants from `scripts.textbook_corpus_integrity_models`.
"""

from __future__ import annotations

import unicodedata
from typing import Any

from scripts.textbook_corpus_integrity_models import (
    CRITICAL_SEVERITIES,
    LIST_NUMBER_PATTERN,
    PAGE_ANCHOR_PATTERN,
    RESOLVED_STATUSES,
    SECTION_NUMBER_PATTERN,
    GateFinding,
    GateResult,
)


def _build_gate_result(
    *,
    gate: str,
    findings: list[GateFinding],
    metrics: dict[str, int],
) -> GateResult:
    critical_count = sum(1 for finding in findings if finding.severity == "critical")
    warning_count = sum(1 for finding in findings if finding.severity != "critical")
    return GateResult(
        gate=gate,
        passed=critical_count == 0,
        critical_count=critical_count,
        warning_count=warning_count,
        metrics=metrics,
        findings=findings,
    )


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_heading(value: str) -> str:
    return _strip_accents(value).casefold()


def _extract_number_key(line: str) -> tuple[int, ...] | None:
    match = LIST_NUMBER_PATTERN.match(line)
    if not match:
        return None
    chapter_value, item_value = match.groups()
    return int(chapter_value), int(item_value)


def _section_kind_from_heading(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("## "):
        return None
    heading = _normalize_heading(stripped[3:].strip())
    if "ovningsuppgifter" in heading:
        return "exercises"
    if "svar" in heading and "losning" in heading:
        return "answers"
    return None


def _collect_section_state(
    *,
    lines: list[str],
    section_kind: str,
) -> tuple[list[int], list[tuple[int, tuple[int, ...]]]]:
    heading_lines: list[int] = []
    entries: list[tuple[int, tuple[int, ...]]] = []
    active_section: str | None = None

    for index, line in enumerate(lines, start=1):
        heading_section = _section_kind_from_heading(line)
        if heading_section is not None:
            active_section = heading_section
            if heading_section == section_kind:
                heading_lines.append(index)
            continue

        if line.strip().startswith("## "):
            active_section = None
            continue

        if active_section != section_kind:
            continue

        key = _extract_number_key(line)
        if key is not None:
            entries.append((index, key))

    return heading_lines, entries


def _number_sequence_findings(
    *,
    numbers_with_lines: list[tuple[int, tuple[int, ...]]],
    value_name: str,
    gap_code: str,
) -> tuple[list[GateFinding], int, int, int]:
    findings: list[GateFinding] = []
    gap_count = 0
    duplicate_count = 0
    regression_count = 0
    seen: set[tuple[int, ...]] = set()
    previous: tuple[int, ...] | None = None

    for line_no, value in numbers_with_lines:
        if value in seen:
            duplicate_count += 1
            findings.append(
                GateFinding(
                    code=f"{value_name.lower()}_numbering_duplicate",
                    severity="critical",
                    line_no=line_no,
                    message=f"{value_name} numbering duplicate detected at {'.'.join(map(str, value))}.",
                )
            )

        if previous is not None and value < previous:
            regression_count += 1
            findings.append(
                GateFinding(
                    code=f"{value_name.lower()}_numbering_regression",
                    severity="critical",
                    line_no=line_no,
                    message=(
                        f"{value_name} numbering regressed from "
                        f"{'.'.join(map(str, previous))} to {'.'.join(map(str, value))}."
                    ),
                )
            )

        if previous is None:
            first_item = value[-1]
            if first_item > 1:
                gap_count += 1
                findings.append(
                    GateFinding(
                        code=gap_code,
                        severity="warning",
                        line_no=line_no,
                        message=(
                            f"{value_name} numbering starts at {'.'.join(map(str, value))}, "
                            "indicating possible OCR numbering omission."
                        ),
                    )
                )
        else:
            if len(previous) == 2 and len(value) == 2:
                previous_chapter, previous_item = previous
                chapter, item = value
                if chapter == previous_chapter and item > previous_item + 1:
                    gap_count += 1
                    findings.append(
                        GateFinding(
                            code=gap_code,
                            severity="warning",
                            line_no=line_no,
                            message=(
                                f"{value_name} numbering jumped from "
                                f"{previous_chapter}.{previous_item} to {chapter}.{item} "
                                "without duplicate/regression."
                            ),
                        )
                    )
                elif chapter > previous_chapter + 1:
                    gap_count += 1
                    findings.append(
                        GateFinding(
                            code=gap_code,
                            severity="warning",
                            line_no=line_no,
                            message=(
                                f"{value_name} chapter numbering jumped from {previous_chapter} "
                                f"to {chapter}."
                            ),
                        )
                    )
                elif chapter > previous_chapter and item > 1:
                    gap_count += 1
                    findings.append(
                        GateFinding(
                            code=gap_code,
                            severity="warning",
                            line_no=line_no,
                            message=(
                                f"{value_name} numbering for chapter {chapter} starts at "
                                f"{chapter}.{item}, indicating possible OCR numbering omission."
                            ),
                        )
                    )
            elif len(previous) == 1 and len(value) == 1 and value[0] > previous[0] + 1:
                gap_count += 1
                findings.append(
                    GateFinding(
                        code=gap_code,
                        severity="warning",
                        line_no=line_no,
                        message=(
                            f"{value_name} numbering jumped from {previous[0]} to {value[0]} "
                            "without duplicate/regression."
                        ),
                    )
                )

        seen.add(value)
        previous = value

    return findings, gap_count, duplicate_count, regression_count


def _row_issue_key(row: dict[str, Any]) -> tuple[str, int]:
    code = str(row.get("code") or "").strip()
    line_no_raw = row.get("line_no")
    line_no = line_no_raw if isinstance(line_no_raw, int) else 0
    return code, line_no


def _is_unresolved_critical_row(row: dict[str, Any]) -> bool:
    severity = str(row.get("severity") or "").strip().casefold()
    status = str(row.get("status") or "unresolved").strip().casefold()
    manual_required = bool(row.get("manual_required"))
    if not manual_required:
        return False
    if severity not in CRITICAL_SEVERITIES:
        return False
    return status not in RESOLVED_STATUSES


def gate_page_anchor_continuity(lines: list[str]) -> GateResult:
    """Validate page-anchor ordering and uniqueness."""
    findings: list[GateFinding] = []
    anchors: list[tuple[int, int]] = []
    for index, line in enumerate(lines, start=1):
        for match in PAGE_ANCHOR_PATTERN.finditer(line):
            anchors.append((index, int(match.group(1))))

    seen_pages: set[int] = set()
    last_page: int | None = None
    duplicate_count = 0
    out_of_order_count = 0
    for line_no, page_no in anchors:
        if page_no in seen_pages:
            duplicate_count += 1
            findings.append(
                GateFinding(
                    code="duplicate_page_anchor",
                    severity="critical",
                    line_no=line_no,
                    message=f"Duplicate page anchor [[page:{page_no}]].",
                )
            )
        if last_page is not None and page_no <= last_page:
            out_of_order_count += 1
            findings.append(
                GateFinding(
                    code="page_anchor_out_of_order",
                    severity="critical",
                    line_no=line_no,
                    message=(
                        f"Page anchor [[page:{page_no}]] is not strictly increasing "
                        f"(previous page={last_page})."
                    ),
                )
            )
        seen_pages.add(page_no)
        last_page = page_no

    return _build_gate_result(
        gate="page_anchor_continuity",
        findings=sorted(findings, key=lambda item: (item.line_no or 0, item.code)),
        metrics={
            "anchor_count": len(anchors),
            "duplicate_count": duplicate_count,
            "out_of_order_count": out_of_order_count,
        },
    )


def gate_section_continuity(lines: list[str]) -> GateResult:
    """Validate monotonic chapter numbering for top-level chapter headings."""
    findings: list[GateFinding] = []
    section_numbers: list[tuple[int, int]] = []

    first_answer_heading_line: int | None = None
    for index, line in enumerate(lines, start=1):
        if _section_kind_from_heading(line) == "answers":
            first_answer_heading_line = index
            break

    for index, line in enumerate(lines, start=1):
        if first_answer_heading_line is not None and index >= first_answer_heading_line:
            break
        match = SECTION_NUMBER_PATTERN.match(line)
        if match:
            stripped = line.strip()
            heading_tail = stripped[3:].strip() if stripped.startswith("## ") else stripped
            first_token = heading_tail.split(" ", maxsplit=1)[0] if heading_tail else ""
            if "." in first_token:
                continue
            section_numbers.append((index, int(match.group(1))))

    duplicate_count = 0
    regression_count = 0
    seen_numbers: set[int] = set()
    previous_number: int | None = None
    for line_no, section_number in section_numbers:
        if section_number in seen_numbers:
            duplicate_count += 1
            findings.append(
                GateFinding(
                    code="section_number_duplicate",
                    severity="warning",
                    line_no=line_no,
                    message=f"Duplicate section number {section_number}.",
                )
            )
        if previous_number is not None and section_number < previous_number:
            regression_count += 1
            findings.append(
                GateFinding(
                    code="section_number_regression",
                    severity="critical",
                    line_no=line_no,
                    message=(f"Section number {section_number} regresses after {previous_number}."),
                )
            )
        seen_numbers.add(section_number)
        previous_number = section_number

    return _build_gate_result(
        gate="section_continuity_anchors",
        findings=sorted(findings, key=lambda item: (item.line_no or 0, item.code)),
        metrics={
            "section_number_count": len(section_numbers),
            "duplicate_count": duplicate_count,
            "regression_count": regression_count,
        },
    )


def gate_exercise_numbering_continuity(lines: list[str]) -> GateResult:
    """Validate exercise list numbering continuity in exercise sections."""
    _, exercise_numbers = _collect_section_state(lines=lines, section_kind="exercises")
    findings, gap_count, duplicate_count, regression_count = _number_sequence_findings(
        numbers_with_lines=exercise_numbers,
        value_name="Exercise",
        gap_code="exercise_numbering_gap",
    )
    return _build_gate_result(
        gate="exercise_numbering_continuity",
        findings=sorted(findings, key=lambda item: (item.line_no or 0, item.code)),
        metrics={
            "exercise_count": len(exercise_numbers),
            "gap_count": gap_count,
            "duplicate_count": duplicate_count,
            "regression_count": regression_count,
        },
    )


def gate_answer_key_mapping_coverage(lines: list[str]) -> GateResult:
    """Validate answer-key heading + mapping coverage against exercises."""
    exercise_heading_lines, exercise_numbers = _collect_section_state(
        lines=lines,
        section_kind="exercises",
    )
    answer_heading_lines, answer_numbers = _collect_section_state(
        lines=lines, section_kind="answers"
    )
    findings: list[GateFinding] = []

    if exercise_numbers and not answer_heading_lines and not answer_numbers:
        first_exercise_line = exercise_numbers[0][0]
        findings.append(
            GateFinding(
                code="missing_answer_heading",
                severity="critical",
                line_no=first_exercise_line,
                message="Exercise section exists but answer structure is missing.",
            )
        )
    elif exercise_numbers and not answer_heading_lines and answer_numbers:
        first_answer_line = answer_numbers[0][0]
        findings.append(
            GateFinding(
                code="answer_entries_without_heading",
                severity="warning",
                line_no=first_answer_line,
                message="Answer-style entries detected without an answer heading block.",
            )
        )

    exercise_set = {value for _, value in exercise_numbers}
    answer_set = {value for _, value in answer_numbers}
    missing_answers = sorted(exercise_set - answer_set)
    extra_answers = sorted(answer_set - exercise_set)

    def _format_key(key: tuple[int, ...]) -> str:
        return ".".join(map(str, key))

    if missing_answers:
        missing_preview = [_format_key(key) for key in missing_answers[:20]]
        severity = "critical" if len(answer_heading_lines) <= 1 else "warning"
        findings.append(
            GateFinding(
                code="answer_key_mapping_gap",
                severity=severity,
                line_no=None,
                message=f"Missing answer mappings for exercises: {missing_preview}.",
            )
        )

    if extra_answers:
        extra_preview = [_format_key(key) for key in extra_answers[:20]]
        findings.append(
            GateFinding(
                code="answer_key_extra_entries",
                severity="warning",
                line_no=None,
                message=f"Answer section has extra entries without exercises: {extra_preview}.",
            )
        )

    return _build_gate_result(
        gate="answer_key_heading_consistency",
        findings=sorted(findings, key=lambda item: (item.line_no or 0, item.code)),
        metrics={
            "exercise_heading_count": len(exercise_heading_lines),
            "answer_heading_count": len(answer_heading_lines),
            "exercise_count": len(exercise_numbers),
            "answer_count": len(answer_numbers),
            "missing_answer_mappings": len(missing_answers),
            "extra_answer_entries": len(extra_answers),
        },
    )


def gate_unresolved_critical_issue_policy(
    manual_queue: list[dict[str, Any]],
    issue_ledger: list[dict[str, Any]],
) -> GateResult:
    """Block when unresolved critical issues remain or queue/ledger drift exists."""
    findings: list[GateFinding] = []
    unresolved_critical_rows = [row for row in manual_queue if _is_unresolved_critical_row(row)]

    if unresolved_critical_rows:
        codes = sorted(
            {
                str(row.get("code") or "unknown")
                for row in unresolved_critical_rows
                if str(row.get("code") or "").strip()
            }
        )
        findings.append(
            GateFinding(
                code="unresolved_critical_issues_present",
                severity="critical",
                line_no=None,
                message=(
                    "Unresolved critical/high manual issues remain and block pristine "
                    f"promotion: {codes}."
                ),
            )
        )

    missing_from_manual_queue: list[tuple[str, int]] = []
    if issue_ledger:
        manual_keys = {_row_issue_key(row) for row in manual_queue}
        for row in issue_ledger:
            if not _is_unresolved_critical_row(row):
                continue
            row_key = _row_issue_key(row)
            if row_key not in manual_keys:
                missing_from_manual_queue.append(row_key)

    if missing_from_manual_queue:
        findings.append(
            GateFinding(
                code="critical_issue_missing_from_manual_queue",
                severity="critical",
                line_no=None,
                message=(
                    "Issue ledger has unresolved critical rows missing in manual queue: "
                    f"{missing_from_manual_queue[:10]}."
                ),
            )
        )

    return _build_gate_result(
        gate="unresolved_critical_issue_policy",
        findings=findings,
        metrics={
            "issue_ledger_rows": len(issue_ledger),
            "manual_queue_rows": len(manual_queue),
            "unresolved_critical_rows": len(unresolved_critical_rows),
            "ledger_missing_in_manual_queue": len(missing_from_manual_queue),
        },
    )


def build_gate_results(
    *,
    lines: list[str],
    manual_queue: list[dict[str, Any]],
    issue_ledger: list[dict[str, Any]],
) -> list[GateResult]:
    """Evaluate all integrity gates in deterministic order."""
    return [
        gate_page_anchor_continuity(lines),
        gate_section_continuity(lines),
        gate_exercise_numbering_continuity(lines),
        gate_answer_key_mapping_coverage(lines),
        gate_unresolved_critical_issue_policy(manual_queue, issue_ledger),
    ]
