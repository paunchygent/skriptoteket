"""Build deterministic mechanical cleanup artifacts for textbook markdown.

Purpose:
    Apply low-risk, deterministic cleanup transforms while preserving semantic content.
    This script explicitly separates mechanical normalization from semantic restoration.

Relationships:
    - Consumes one markdown source file from a reconciled corpus baseline.
    - Produces mechanical markdown output plus issue ledgers and manual queue artifacts.
    - Intended to feed PR-0075 manual restoration workflow without mutating source files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path(".artifacts/textbook_corpus/mechanical")
PROTECTED_SECTION_RE = re.compile(
    r"^\s*##\s+.*(?:ovningsuppgifter|övningsuppgifter|svar|losningar|lösningar)",
    re.IGNORECASE,
)
HEADING_ARTIFACT_RE = re.compile(r"\.{3,}\d*$")
HEADING_CANONICAL_MAP = {
    "svar och losningar": "## SVAR OCH LOSNINGAR",
    "svar och losningar.": "## SVAR OCH LOSNINGAR",
    "svar och losningar:": "## SVAR OCH LOSNINGAR",
    "svar och losningar ": "## SVAR OCH LOSNINGAR",
    "svar och losningar....": "## SVAR OCH LOSNINGAR",
}


@dataclass(frozen=True, slots=True)
class TransformEvent:
    """Represents one deterministic transform event."""

    code: str
    line_no: int
    before: str
    after: str


@dataclass(frozen=True, slots=True)
class IssueEvent:
    """Represents one issue emitted to the ledger/manual queue."""

    code: str
    line_no: int
    severity: str
    manual_required: bool
    protected_zone: bool
    message: str
    line_text: str


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Pure result for deterministic cleanup of one markdown document."""

    cleaned_markdown: str
    transforms: list[TransformEvent]
    issues: list[IssueEvent]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-markdown", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=350,
        help="Emit manual-review issue when line length exceeds this threshold.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _canonicalize_heading(line: str) -> str:
    stripped = line.strip()
    if not stripped.startswith("## "):
        return line
    heading_value = stripped[3:].strip().casefold()
    normalized = HEADING_CANONICAL_MAP.get(heading_value)
    return normalized if normalized else line


def _is_page_number_candidate(
    *,
    current_line: str,
    previous_line: str | None,
    next_line: str | None,
) -> bool:
    current = current_line.strip()
    if not current.isdigit():
        return False
    if len(current) > 4:
        return False
    if previous_line is None or next_line is None:
        return False
    return previous_line.strip() == "" and next_line.strip() == ""


def cleanup_textbook_markdown(*, text: str, max_line_length: int) -> CleanupResult:
    """Return deterministic mechanical cleanup output and issue events.

    Rules:
      - Safe transforms only: tabs/trailing-space cleanup, explicit page anchors, bounded blank lines.
      - No-autofix in protected semantic zones.
      - All uncertain/high-risk patterns are emitted to manual queue issues.
    """
    original_lines = text.splitlines()
    first_pass_lines: list[str] = []
    transforms: list[TransformEvent] = []
    issues: list[IssueEvent] = []

    in_protected_zone = False
    for idx, line in enumerate(original_lines):
        line_no = idx + 1
        candidate = line

        heading_candidate = _canonicalize_heading(candidate)
        if heading_candidate != candidate:
            transforms.append(
                TransformEvent(
                    code="heading_canonicalized",
                    line_no=line_no,
                    before=candidate,
                    after=heading_candidate,
                )
            )
            candidate = heading_candidate

        if candidate.strip().startswith("## "):
            in_protected_zone = bool(PROTECTED_SECTION_RE.search(candidate))

        tab_replaced = candidate.replace("\t", "    ")
        if tab_replaced != candidate:
            transforms.append(
                TransformEvent(
                    code="tab_expanded",
                    line_no=line_no,
                    before=candidate,
                    after=tab_replaced,
                )
            )
            candidate = tab_replaced

        trimmed = candidate.rstrip()
        if trimmed != candidate:
            transforms.append(
                TransformEvent(
                    code="trailing_whitespace_trimmed",
                    line_no=line_no,
                    before=candidate,
                    after=trimmed,
                )
            )
            candidate = trimmed

        previous_line = original_lines[idx - 1] if idx > 0 else None
        next_line = original_lines[idx + 1] if idx + 1 < len(original_lines) else None
        if _is_page_number_candidate(
            current_line=candidate,
            previous_line=previous_line,
            next_line=next_line,
        ):
            if in_protected_zone:
                issues.append(
                    IssueEvent(
                        code="protected_zone_page_anchor_candidate",
                        line_no=line_no,
                        severity="high",
                        manual_required=True,
                        protected_zone=True,
                        message="Standalone numeric line in protected zone requires manual confirmation.",
                        line_text=candidate,
                    )
                )
            else:
                anchored = f"[[page:{candidate.strip()}]]"
                transforms.append(
                    TransformEvent(
                        code="page_anchor_inserted",
                        line_no=line_no,
                        before=candidate,
                        after=anchored,
                    )
                )
                candidate = anchored

        if len(candidate) > max_line_length:
            issues.append(
                IssueEvent(
                    code="long_line_extreme",
                    line_no=line_no,
                    severity="high",
                    manual_required=True,
                    protected_zone=in_protected_zone,
                    message=f"Line length {len(candidate)} exceeds threshold {max_line_length}.",
                    line_text=candidate,
                )
            )

        if candidate.strip().startswith("## ") and HEADING_ARTIFACT_RE.search(candidate.strip()):
            issues.append(
                IssueEvent(
                    code="heading_artifact_dots",
                    line_no=line_no,
                    severity="medium",
                    manual_required=True,
                    protected_zone=in_protected_zone,
                    message="Heading contains OCR dot artifact and may require manual restoration.",
                    line_text=candidate,
                )
            )

        if "<!-- image -->" in candidate:
            issues.append(
                IssueEvent(
                    code="image_marker_present",
                    line_no=line_no,
                    severity="low",
                    manual_required=False,
                    protected_zone=in_protected_zone,
                    message="Image marker retained; verify nearby context during manual pass.",
                    line_text=candidate,
                )
            )

        first_pass_lines.append(candidate)

    collapsed_lines: list[str] = []
    blank_streak = 0
    for idx, line in enumerate(first_pass_lines):
        line_no = idx + 1
        if line.strip() == "":
            blank_streak += 1
            if blank_streak > 2:
                transforms.append(
                    TransformEvent(
                        code="blank_line_collapsed",
                        line_no=line_no,
                        before=line,
                        after="",
                    )
                )
                continue
        else:
            blank_streak = 0
        collapsed_lines.append(line)

    cleaned = "\n".join(collapsed_lines).rstrip() + "\n"
    return CleanupResult(cleaned_markdown=cleaned, transforms=transforms, issues=issues)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, object], *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]], *, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    args = _parse_args()
    input_markdown = args.input_markdown.resolve()
    output_dir = args.output_dir.resolve()

    source_text = input_markdown.read_text(encoding="utf-8")
    result = cleanup_textbook_markdown(text=source_text, max_line_length=args.max_line_length)
    source_stem = input_markdown.stem

    cleaned_path = output_dir / "mechanical" / f"{source_stem}.mechanical.md"
    ledger_path = output_dir / "ledgers" / f"{source_stem}.issue-ledger.jsonl"
    manual_queue_path = output_dir / "ledgers" / f"{source_stem}.manual-queue.jsonl"
    transform_log_path = output_dir / "ledgers" / f"{source_stem}.transform-log.json"
    summary_path = output_dir / "summary" / f"{source_stem}.summary.json"

    if not args.dry_run:
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned_path.write_text(result.cleaned_markdown, encoding="utf-8")

    issue_rows = [asdict(item) for item in result.issues]
    manual_rows = [row for row in issue_rows if bool(row.get("manual_required"))]
    _write_jsonl(ledger_path, issue_rows, dry_run=args.dry_run)
    _write_jsonl(manual_queue_path, manual_rows, dry_run=args.dry_run)

    transform_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_markdown": str(input_markdown),
        "transforms": [asdict(event) for event in result.transforms],
    }
    _write_json(transform_log_path, transform_payload, dry_run=args.dry_run)

    summary_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_markdown": str(input_markdown),
        "cleaned_markdown_path": str(cleaned_path),
        "source_sha256": _sha256_text(source_text),
        "cleaned_sha256": _sha256_text(result.cleaned_markdown),
        "transform_count": len(result.transforms),
        "issue_count": len(issue_rows),
        "manual_queue_count": len(manual_rows),
    }
    _write_json(summary_path, summary_payload, dry_run=args.dry_run)

    print(f"[textbook_mechanical_cleanup] cleaned={cleaned_path}")
    print(f"[textbook_mechanical_cleanup] issue_ledger={ledger_path}")
    print(f"[textbook_mechanical_cleanup] manual_queue={manual_queue_path}")
    print(
        "[textbook_mechanical_cleanup] "
        f"transforms={len(result.transforms)} issues={len(issue_rows)} manual_queue={len(manual_rows)}"
    )


if __name__ == "__main__":
    main()
