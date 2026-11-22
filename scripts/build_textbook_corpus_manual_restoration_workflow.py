"""Build and apply a manual restoration workflow for textbook corpus repairs.

Purpose:
    Provide a structured, auditable workflow for semantically important textbook fixes.
    The workflow is multi-agent friendly: issue packetization, patch schema validation,
    verifier gating, and deterministic patch application.

Relationships:
    - Reads manual-queue JSONL emitted by mechanical cleanup.
    - Writes issue packets and patch templates under an artifact/work directory.
    - Validates patch YAML files under `manual_fixes/`.
    - Applies approved patches to an input markdown copy (never in-place).
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import NotRequired, TypedDict

import yaml
from pydantic import JsonValue

ISSUE_VERSION = 1
PATCH_VERSION = 1
PATCH_STATUS_ALLOWED = {"proposed", "approved", "rejected"}


class ManualQueueRow(TypedDict, total=False):
    """One manual-queue JSONL row read by fixed keys during issue loading.

    Every field is tolerated defensively: the loader coerces arbitrary JSON
    values with ``str``/``bool``/``isinstance`` rather than trusting the
    on-disk types.
    """

    code: JsonValue
    line_no: JsonValue
    severity: JsonValue
    protected_zone: JsonValue
    message: JsonValue
    line_text: JsonValue


class PatchSourcePayload(TypedDict, total=False):
    """Subset of a patch ``source`` object read during validation/apply."""

    line_no: JsonValue
    expected_original: JsonValue


class PatchChangePayload(TypedDict, total=False):
    """Subset of a patch ``change`` object read during validation/apply."""

    mode: JsonValue
    replacement: JsonValue


class PatchReviewPayload(TypedDict, total=False):
    """Subset of a patch ``review`` object read during validation."""

    decision: JsonValue
    notes: JsonValue


class ManualPatchPayload(TypedDict, total=False):
    """One manual patch YAML document read by fixed keys.

    Nested ``source``/``change``/``review`` objects are parsed into their own
    payload views only when the raw value is an object, so validation keeps
    distinguishing "missing or non-object" from "object with bad fields"
    exactly like the untyped reader did.
    """

    version: JsonValue
    patch_id: JsonValue
    issue_id: JsonValue
    status: JsonValue
    author: JsonValue
    verifier: JsonValue
    verified_at: JsonValue
    source: PatchSourcePayload
    change: PatchChangePayload
    review: PatchReviewPayload


class IssueIndexRow(TypedDict):
    """Serialized form of one `WorkflowIssue` in packets and the issue index."""

    issue_id: str
    code: str
    line_no: int
    severity: str
    protected_zone: bool
    message: str
    line_text: str


class IssueIndexReport(TypedDict):
    """Issue-index JSON report returned by `generate_packets`."""

    generated_at: str
    manual_queue_path: str
    issue_count: int
    packet_count: int
    issues: list[IssueIndexRow]


class PacketAssignment(TypedDict):
    """``assignment`` block of one issue packet YAML document."""

    owner: str
    verifier: str


class PacketPayload(TypedDict):
    """One issue packet YAML document written by `generate_packets`."""

    version: int
    packet_id: str
    generated_at: str
    manual_queue_path: str
    assignment: PacketAssignment
    issue_ids: list[str]
    issues: list[IssueIndexRow]


class PatchValidationSummary(TypedDict):
    """Summary block of the patch validation report."""

    files_total: int
    valid_total: int
    invalid_total: int
    approved_total: int
    rejected_total: int
    proposed_total: int
    cross_file_errors: int


class PatchValidationResultRow(TypedDict):
    """One per-file row in the patch validation report."""

    file_path: str
    patch_id: str | None
    issue_id: str | None
    status: str | None
    valid: bool
    errors: list[str]


class CrossFileErrorRow(TypedDict):
    """One cross-file uniqueness error in the patch validation report."""

    file: str
    error: str


class PatchValidationReport(TypedDict):
    """Machine-readable patch validation report written to JSON."""

    generated_at: str
    patch_dir: str
    summary: PatchValidationSummary
    results: list[PatchValidationResultRow]
    cross_file_errors: list[CrossFileErrorRow]


class AppliedRow(TypedDict):
    """One successfully applied patch row in the apply report."""

    patch_id: str
    issue_id: str
    line_no: int


class ApplyFailureRow(TypedDict):
    """One failed patch application row in the apply report."""

    patch_id: str
    error: str
    line_no: NotRequired[int]


class PatchApplyReport(TypedDict, total=False):
    """Apply report written to JSON; checksum fields only appear on success."""

    generated_at: str
    input_markdown: str
    output_markdown: str
    snapshot_path: str
    input_sha256: str
    output_sha256: str
    applied_count: int
    failure_count: int
    applied: list[AppliedRow]
    failures: list[ApplyFailureRow]


@dataclass(frozen=True, slots=True)
class WorkflowIssue:
    """Represents one manual-queue issue with deterministic identity."""

    issue_id: str
    code: str
    line_no: int
    severity: str
    protected_zone: bool
    message: str
    line_text: str


@dataclass(frozen=True, slots=True)
class PatchValidation:
    """Validation result for one manual patch file."""

    file_path: str
    patch_id: str | None
    issue_id: str | None
    status: str | None
    valid: bool
    errors: list[str]
    payload: ManualPatchPayload | None


def _parse_manual_queue_row(value: JsonValue) -> ManualQueueRow | None:
    """Parse one JSONL row; non-objects are skipped like the old dict filter.

    Fields are copied verbatim: ``_load_workflow_issues`` applies the same
    ``str``/``bool``/``int`` coercions the untyped reader did.
    """
    if not isinstance(value, dict):
        return None
    row = ManualQueueRow()
    if "code" in value:
        row["code"] = value["code"]
    if "line_no" in value:
        row["line_no"] = value["line_no"]
    if "severity" in value:
        row["severity"] = value["severity"]
    if "protected_zone" in value:
        row["protected_zone"] = value["protected_zone"]
    if "message" in value:
        row["message"] = value["message"]
    if "line_text" in value:
        row["line_text"] = value["line_text"]
    return row


def _parse_patch_source(value: JsonValue) -> PatchSourcePayload | None:
    """Parse a patch ``source`` block; non-objects yield ``None`` (missing)."""
    if not isinstance(value, dict):
        return None
    payload = PatchSourcePayload()
    if "line_no" in value:
        payload["line_no"] = value["line_no"]
    if "expected_original" in value:
        payload["expected_original"] = value["expected_original"]
    return payload


def _parse_patch_change(value: JsonValue) -> PatchChangePayload | None:
    """Parse a patch ``change`` block; non-objects yield ``None`` (missing)."""
    if not isinstance(value, dict):
        return None
    payload = PatchChangePayload()
    if "mode" in value:
        payload["mode"] = value["mode"]
    if "replacement" in value:
        payload["replacement"] = value["replacement"]
    return payload


def _parse_patch_review(value: JsonValue) -> PatchReviewPayload | None:
    """Parse a patch ``review`` block; non-objects yield ``None`` (missing)."""
    if not isinstance(value, dict):
        return None
    payload = PatchReviewPayload()
    if "decision" in value:
        payload["decision"] = value["decision"]
    if "notes" in value:
        payload["notes"] = value["notes"]
    return payload


def _parse_manual_patch_payload(value: JsonValue) -> ManualPatchPayload | None:
    """Parse one patch YAML document; non-objects yield ``None``."""
    if not isinstance(value, dict):
        return None
    payload = ManualPatchPayload()
    if "version" in value:
        payload["version"] = value["version"]
    if "patch_id" in value:
        payload["patch_id"] = value["patch_id"]
    if "issue_id" in value:
        payload["issue_id"] = value["issue_id"]
    if "status" in value:
        payload["status"] = value["status"]
    if "author" in value:
        payload["author"] = value["author"]
    if "verifier" in value:
        payload["verifier"] = value["verifier"]
    if "verified_at" in value:
        payload["verified_at"] = value["verified_at"]
    source = _parse_patch_source(value.get("source"))
    if source is not None:
        payload["source"] = source
    change = _parse_patch_change(value.get("change"))
    if change is not None:
        payload["change"] = change
    review = _parse_patch_review(value.get("review"))
    if review is not None:
        payload["review"] = review
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    packets = subparsers.add_parser("generate-packets")
    packets.add_argument("--manual-queue", type=Path, required=True)
    packets.add_argument("--output-dir", type=Path, required=True)
    packets.add_argument("--packet-size", type=int, default=12)
    packets.add_argument(
        "--scaffold-patches",
        action="store_true",
        help="Create proposed patch YAML templates for each issue under manual_fixes/.",
    )

    validate = subparsers.add_parser("validate-patches")
    validate.add_argument("--patch-dir", type=Path, required=True)
    validate.add_argument("--report-path", type=Path, required=True)

    apply_cmd = subparsers.add_parser("apply-patches")
    apply_cmd.add_argument("--input-markdown", type=Path, required=True)
    apply_cmd.add_argument("--patch-dir", type=Path, required=True)
    apply_cmd.add_argument("--output-markdown", type=Path, required=True)
    apply_cmd.add_argument("--report-path", type=Path, required=True)
    apply_cmd.add_argument("--snapshot-path", type=Path, required=True)

    return parser.parse_args()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[ManualQueueRow]:
    rows: list[ManualQueueRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        obj: JsonValue = json.loads(stripped)
        row = _parse_manual_queue_row(obj)
        if row is not None:
            rows.append(row)
    return rows


_JsonReportPayload = IssueIndexReport | PatchValidationReport | PatchApplyReport

_YamlReportPayload = Mapping[str, JsonValue] | PacketPayload


def _write_json(path: Path, payload: _JsonReportPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_yaml(path: Path, payload: _YamlReportPayload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")


def _issue_to_json(issue: WorkflowIssue) -> IssueIndexRow:
    return {
        "issue_id": issue.issue_id,
        "code": issue.code,
        "line_no": issue.line_no,
        "severity": issue.severity,
        "protected_zone": issue.protected_zone,
        "message": issue.message,
        "line_text": issue.line_text,
    }


def _int_or_zero(value: JsonValue | None) -> int:
    candidate = value or 0
    if isinstance(candidate, (dict, list)):
        raise TypeError(
            f"int() argument must be a string or a real number, not {type(candidate).__name__!r}"
        )
    return int(candidate)


def _build_issue_id(index: int, code: str, line_no: int) -> str:
    normalized_code = "".join(ch for ch in code.upper() if ch.isalnum() or ch == "_")
    return f"ISSUE-{index:05d}-L{line_no:05d}-{normalized_code}"


def _load_workflow_issues(manual_queue_path: Path) -> list[WorkflowIssue]:
    rows = _read_jsonl(manual_queue_path)
    issues: list[WorkflowIssue] = []
    for index, row in enumerate(rows, start=1):
        code = str(row.get("code") or "UNKNOWN")
        line_no_obj = row.get("line_no")
        line_no = int(line_no_obj) if isinstance(line_no_obj, int) else 0
        issue = WorkflowIssue(
            issue_id=_build_issue_id(index=index, code=code, line_no=line_no),
            code=code,
            line_no=line_no,
            severity=str(row.get("severity") or "unknown"),
            protected_zone=bool(row.get("protected_zone")),
            message=str(row.get("message") or ""),
            line_text=str(row.get("line_text") or ""),
        )
        issues.append(issue)
    return issues


def generate_packets(
    *,
    manual_queue_path: Path,
    output_dir: Path,
    packet_size: int,
    scaffold_patches: bool,
) -> IssueIndexReport:
    """Generate deterministic issue packets and optional patch templates."""
    issues = _load_workflow_issues(manual_queue_path)
    packets_dir = output_dir / "packets"
    fixes_dir = output_dir / "manual_fixes"

    packet_count = 0
    for start_idx in range(0, len(issues), packet_size):
        packet_count += 1
        packet_issues = issues[start_idx : start_idx + packet_size]
        packet_id = f"PKT-{packet_count:04d}"
        packet_issue_rows: list[IssueIndexRow] = [_issue_to_json(item) for item in packet_issues]
        payload = PacketPayload(
            version=ISSUE_VERSION,
            packet_id=packet_id,
            generated_at=datetime.now(UTC).isoformat(),
            manual_queue_path=str(manual_queue_path),
            assignment=PacketAssignment(owner="", verifier=""),
            issue_ids=[item.issue_id for item in packet_issues],
            issues=packet_issue_rows,
        )
        _write_yaml(packets_dir / f"{packet_id}.yaml", payload)

    if scaffold_patches:
        for issue in issues:
            patch_payload: dict[str, JsonValue] = {
                "version": PATCH_VERSION,
                "patch_id": f"PATCH-{issue.issue_id}",
                "issue_id": issue.issue_id,
                "status": "proposed",
                "author": "",
                "verifier": "",
                "verified_at": "",
                "rationale": "",
                "source": {
                    "line_no": issue.line_no,
                    "expected_original": issue.line_text,
                },
                "change": {
                    "mode": "replace_line",
                    "replacement": issue.line_text,
                },
                "review": {
                    "decision": "pending",
                    "notes": "",
                },
            }
            _write_yaml(fixes_dir / f"{issue.issue_id}.yaml", patch_payload)

    issue_index_rows: list[IssueIndexRow] = [_issue_to_json(item) for item in issues]
    issue_index_payload = IssueIndexReport(
        generated_at=datetime.now(UTC).isoformat(),
        manual_queue_path=str(manual_queue_path),
        issue_count=len(issues),
        packet_count=packet_count,
        issues=issue_index_rows,
    )
    _write_json(output_dir / "issue-index.json", issue_index_payload)
    return issue_index_payload


def _read_yaml_file(path: Path) -> ManualPatchPayload | None:
    try:
        payload: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    return _parse_manual_patch_payload(payload)


def _validate_patch_payload(path: Path, payload: ManualPatchPayload | None) -> PatchValidation:
    errors: list[str] = []
    if payload is None:
        return PatchValidation(
            file_path=str(path),
            patch_id=None,
            issue_id=None,
            status=None,
            valid=False,
            errors=["invalid_yaml_or_non_object"],
            payload=None,
        )

    patch_id = payload.get("patch_id")
    issue_id = payload.get("issue_id")
    status = payload.get("status")
    author = payload.get("author")
    verifier = payload.get("verifier")
    verified_at = payload.get("verified_at")
    source = payload.get("source")
    change = payload.get("change")
    review = payload.get("review")

    if payload.get("version") != PATCH_VERSION:
        errors.append("unsupported_version")
    if not isinstance(patch_id, str) or patch_id.strip() == "":
        errors.append("missing_patch_id")
    if not isinstance(issue_id, str) or issue_id.strip() == "":
        errors.append("missing_issue_id")
    if not isinstance(status, str) or status not in PATCH_STATUS_ALLOWED:
        errors.append("invalid_status")
    if source is None:
        errors.append("missing_source")
    else:
        source_line_no = source.get("line_no")
        if not isinstance(source_line_no, int) or source_line_no <= 0:
            errors.append("invalid_source_line_no")
        if not isinstance(source.get("expected_original"), str):
            errors.append("invalid_expected_original")
    if change is None:
        errors.append("missing_change")
    else:
        if change.get("mode") != "replace_line":
            errors.append("unsupported_change_mode")
        if not isinstance(change.get("replacement"), str):
            errors.append("invalid_replacement")
    if review is None:
        errors.append("missing_review")

    if status == "approved":
        if not isinstance(author, str) or author.strip() == "":
            errors.append("approved_missing_author")
        if not isinstance(verifier, str) or verifier.strip() == "":
            errors.append("approved_missing_verifier")
        if (
            isinstance(author, str)
            and isinstance(verifier, str)
            and author.strip()
            and verifier.strip()
            and author.strip() == verifier.strip()
        ):
            errors.append("self_approval_not_allowed")
        if not isinstance(verified_at, str) or verified_at.strip() == "":
            errors.append("approved_missing_verified_at")
        if review is None or review.get("decision") != "approved":
            errors.append("approved_missing_review_decision")

    return PatchValidation(
        file_path=str(path),
        patch_id=patch_id if isinstance(patch_id, str) else None,
        issue_id=issue_id if isinstance(issue_id, str) else None,
        status=status if isinstance(status, str) else None,
        valid=not errors,
        errors=errors,
        payload=payload,
    )


def validate_patches(*, patch_dir: Path, report_path: Path) -> PatchValidationReport:
    """Validate patch schema and cross-file uniqueness rules."""
    results: list[PatchValidation] = []
    for path in sorted(patch_dir.glob("*.yaml")):
        payload = _read_yaml_file(path)
        results.append(_validate_patch_payload(path, payload))

    issue_ids_seen: set[str] = set()
    patch_ids_seen: set[str] = set()
    cross_file_errors: list[CrossFileErrorRow] = []
    for result in results:
        if result.issue_id:
            if result.issue_id in issue_ids_seen:
                cross_file_errors.append(
                    CrossFileErrorRow(
                        file=result.file_path, error="duplicate_issue_id_across_files"
                    )
                )
            issue_ids_seen.add(result.issue_id)
        if result.patch_id:
            if result.patch_id in patch_ids_seen:
                cross_file_errors.append(
                    CrossFileErrorRow(
                        file=result.file_path, error="duplicate_patch_id_across_files"
                    )
                )
            patch_ids_seen.add(result.patch_id)

    report = PatchValidationReport(
        generated_at=datetime.now(UTC).isoformat(),
        patch_dir=str(patch_dir),
        summary=PatchValidationSummary(
            files_total=len(results),
            valid_total=sum(1 for item in results if item.valid),
            invalid_total=sum(1 for item in results if not item.valid),
            approved_total=sum(1 for item in results if item.status == "approved"),
            rejected_total=sum(1 for item in results if item.status == "rejected"),
            proposed_total=sum(1 for item in results if item.status == "proposed"),
            cross_file_errors=len(cross_file_errors),
        ),
        results=[
            PatchValidationResultRow(
                file_path=item.file_path,
                patch_id=item.patch_id,
                issue_id=item.issue_id,
                status=item.status,
                valid=item.valid,
                errors=item.errors,
            )
            for item in results
        ],
        cross_file_errors=cross_file_errors,
    )
    _write_json(report_path, report)
    return report


def apply_patches(
    *,
    input_markdown: Path,
    patch_dir: Path,
    output_markdown: Path,
    report_path: Path,
    snapshot_path: Path,
) -> PatchApplyReport:
    """Apply approved patches deterministically to a copy of markdown lines."""
    validation_report = validate_patches(
        patch_dir=patch_dir,
        report_path=report_path.with_suffix(".validation.json"),
    )
    if validation_report["summary"]["invalid_total"] > 0:
        raise SystemExit("Cannot apply patches: invalid patch schema entries detected.")
    if validation_report["summary"]["cross_file_errors"] > 0:
        raise SystemExit("Cannot apply patches: cross-file uniqueness errors detected.")

    input_text = input_markdown.read_text(encoding="utf-8")
    original_lines = input_text.splitlines()
    lines = list(original_lines)

    patch_rows: list[ManualPatchPayload] = []
    for file_path in sorted(patch_dir.glob("*.yaml")):
        payload = _read_yaml_file(file_path)
        if payload is None:
            continue
        if payload.get("status") != "approved":
            continue
        patch_rows.append(payload)

    patch_rows.sort(key=_patch_sort_key)

    seen_issue_ids: set[str] = set()
    seen_line_nos: set[int] = set()
    apply_failures: list[ApplyFailureRow] = []
    applied: list[AppliedRow] = []

    for row in patch_rows:
        patch_id = str(row.get("patch_id") or "")
        issue_id = str(row.get("issue_id") or "")
        source = row.get("source") or PatchSourcePayload()
        change = row.get("change") or PatchChangePayload()
        line_no = _int_or_zero(source.get("line_no"))
        expected = str(source.get("expected_original") or "")
        replacement = str(change.get("replacement") or "")

        if issue_id in seen_issue_ids:
            apply_failures.append(ApplyFailureRow(patch_id=patch_id, error="duplicate_issue_id"))
            continue
        seen_issue_ids.add(issue_id)

        if line_no in seen_line_nos:
            apply_failures.append(ApplyFailureRow(patch_id=patch_id, error="duplicate_line_no"))
            continue
        seen_line_nos.add(line_no)

        if line_no <= 0 or line_no > len(lines):
            apply_failures.append(ApplyFailureRow(patch_id=patch_id, error="line_out_of_range"))
            continue

        current = lines[line_no - 1]
        if current != expected:
            apply_failures.append(
                ApplyFailureRow(
                    patch_id=patch_id,
                    error="expected_original_mismatch",
                    line_no=line_no,
                )
            )
            continue

        lines[line_no - 1] = replacement
        applied.append(AppliedRow(patch_id=patch_id, issue_id=issue_id, line_no=line_no))

    if apply_failures:
        report = PatchApplyReport(
            generated_at=datetime.now(UTC).isoformat(),
            input_markdown=str(input_markdown),
            output_markdown=str(output_markdown),
            snapshot_path=str(snapshot_path),
            applied_count=len(applied),
            failure_count=len(apply_failures),
            applied=applied,
            failures=apply_failures,
        )
        _write_json(report_path, report)
        raise SystemExit("Patch application failed. See apply report for details.")

    output_text = "\n".join(lines).rstrip() + "\n"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(input_text, encoding="utf-8")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(output_text, encoding="utf-8")

    report = PatchApplyReport(
        generated_at=datetime.now(UTC).isoformat(),
        input_markdown=str(input_markdown),
        output_markdown=str(output_markdown),
        snapshot_path=str(snapshot_path),
        input_sha256=_sha256_text(input_text),
        output_sha256=_sha256_text(output_text),
        applied_count=len(applied),
        failure_count=0,
        applied=applied,
        failures=[],
    )
    _write_json(report_path, report)
    return report


def _patch_sort_key(row: ManualPatchPayload) -> tuple[int, str]:
    source = row.get("source") or PatchSourcePayload()
    return (_int_or_zero(source.get("line_no")), str(row.get("patch_id") or ""))


def main() -> None:
    args = _parse_args()
    if args.command == "generate-packets":
        report = generate_packets(
            manual_queue_path=args.manual_queue.resolve(),
            output_dir=args.output_dir.resolve(),
            packet_size=max(args.packet_size, 1),
            scaffold_patches=bool(args.scaffold_patches),
        )
        print(
            "[textbook_manual_workflow] "
            f"generated_packets={report['packet_count']} issues={report['issue_count']}"
        )
        return

    if args.command == "validate-patches":
        report = validate_patches(
            patch_dir=args.patch_dir.resolve(),
            report_path=args.report_path.resolve(),
        )
        summary = report["summary"]
        print(
            "[textbook_manual_workflow] "
            f"validated={summary['files_total']} valid={summary['valid_total']} "
            f"invalid={summary['invalid_total']} cross_file_errors={summary['cross_file_errors']}"
        )
        if summary["invalid_total"] > 0 or summary["cross_file_errors"] > 0:
            raise SystemExit(1)
        return

    if args.command == "apply-patches":
        report = apply_patches(
            input_markdown=args.input_markdown.resolve(),
            patch_dir=args.patch_dir.resolve(),
            output_markdown=args.output_markdown.resolve(),
            report_path=args.report_path.resolve(),
            snapshot_path=args.snapshot_path.resolve(),
        )
        print(
            "[textbook_manual_workflow] "
            f"applied={report['applied_count']} failures={report['failure_count']}"
        )
        return

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
