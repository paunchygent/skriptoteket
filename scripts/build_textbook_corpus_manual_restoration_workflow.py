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
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

ISSUE_VERSION = 1
PATCH_VERSION = 1
PATCH_STATUS_ALLOWED = {"proposed", "approved", "rejected"}


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
    payload: dict[str, Any] | None


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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(text, encoding="utf-8")


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
) -> dict[str, Any]:
    """Generate deterministic issue packets and optional patch templates."""
    issues = _load_workflow_issues(manual_queue_path)
    packets_dir = output_dir / "packets"
    fixes_dir = output_dir / "manual_fixes"

    packet_count = 0
    for start_idx in range(0, len(issues), packet_size):
        packet_count += 1
        packet_issues = issues[start_idx : start_idx + packet_size]
        packet_id = f"PKT-{packet_count:04d}"
        payload = {
            "version": ISSUE_VERSION,
            "packet_id": packet_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "manual_queue_path": str(manual_queue_path),
            "assignment": {
                "owner": "",
                "verifier": "",
            },
            "issue_ids": [item.issue_id for item in packet_issues],
            "issues": [asdict(item) for item in packet_issues],
        }
        _write_yaml(packets_dir / f"{packet_id}.yaml", payload)

    if scaffold_patches:
        for issue in issues:
            patch_payload = {
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

    issue_index_payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "manual_queue_path": str(manual_queue_path),
        "issue_count": len(issues),
        "packet_count": packet_count,
        "issues": [asdict(item) for item in issues],
    }
    _write_json(output_dir / "issue-index.json", issue_index_payload)
    return issue_index_payload


def _read_yaml_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _validate_patch_payload(path: Path, payload: dict[str, Any] | None) -> PatchValidation:
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
    if not isinstance(source, dict):
        errors.append("missing_source")
    else:
        if not isinstance(source.get("line_no"), int) or source.get("line_no") <= 0:
            errors.append("invalid_source_line_no")
        if not isinstance(source.get("expected_original"), str):
            errors.append("invalid_expected_original")
    if not isinstance(change, dict):
        errors.append("missing_change")
    else:
        if change.get("mode") != "replace_line":
            errors.append("unsupported_change_mode")
        if not isinstance(change.get("replacement"), str):
            errors.append("invalid_replacement")
    if not isinstance(review, dict):
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
        if not isinstance(review, dict) or review.get("decision") != "approved":
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


def validate_patches(*, patch_dir: Path, report_path: Path) -> dict[str, Any]:
    """Validate patch schema and cross-file uniqueness rules."""
    results: list[PatchValidation] = []
    for path in sorted(patch_dir.glob("*.yaml")):
        payload = _read_yaml_file(path)
        results.append(_validate_patch_payload(path, payload))

    issue_ids_seen: set[str] = set()
    patch_ids_seen: set[str] = set()
    cross_file_errors: list[dict[str, str]] = []
    for result in results:
        if result.issue_id:
            if result.issue_id in issue_ids_seen:
                cross_file_errors.append(
                    {"file": result.file_path, "error": "duplicate_issue_id_across_files"}
                )
            issue_ids_seen.add(result.issue_id)
        if result.patch_id:
            if result.patch_id in patch_ids_seen:
                cross_file_errors.append(
                    {"file": result.file_path, "error": "duplicate_patch_id_across_files"}
                )
            patch_ids_seen.add(result.patch_id)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "patch_dir": str(patch_dir),
        "summary": {
            "files_total": len(results),
            "valid_total": sum(1 for item in results if item.valid),
            "invalid_total": sum(1 for item in results if not item.valid),
            "approved_total": sum(1 for item in results if item.status == "approved"),
            "rejected_total": sum(1 for item in results if item.status == "rejected"),
            "proposed_total": sum(1 for item in results if item.status == "proposed"),
            "cross_file_errors": len(cross_file_errors),
        },
        "results": [
            {
                "file_path": item.file_path,
                "patch_id": item.patch_id,
                "issue_id": item.issue_id,
                "status": item.status,
                "valid": item.valid,
                "errors": item.errors,
            }
            for item in results
        ],
        "cross_file_errors": cross_file_errors,
    }
    _write_json(report_path, report)
    return report


def apply_patches(
    *,
    input_markdown: Path,
    patch_dir: Path,
    output_markdown: Path,
    report_path: Path,
    snapshot_path: Path,
) -> dict[str, Any]:
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

    patch_rows: list[dict[str, Any]] = []
    for file_path in sorted(patch_dir.glob("*.yaml")):
        payload = _read_yaml_file(file_path)
        if payload is None:
            continue
        if payload.get("status") != "approved":
            continue
        patch_rows.append(payload)

    patch_rows.sort(
        key=lambda row: (
            int(_as_object(row.get("source")).get("line_no") or 0),
            str(row.get("patch_id") or ""),
        )
    )

    seen_issue_ids: set[str] = set()
    seen_line_nos: set[int] = set()
    apply_failures: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for row in patch_rows:
        patch_id = str(row.get("patch_id") or "")
        issue_id = str(row.get("issue_id") or "")
        source = _as_object(row.get("source"))
        change = _as_object(row.get("change"))
        line_no = int(source.get("line_no") or 0)
        expected = str(source.get("expected_original") or "")
        replacement = str(change.get("replacement") or "")

        if issue_id in seen_issue_ids:
            apply_failures.append({"patch_id": patch_id, "error": "duplicate_issue_id"})
            continue
        seen_issue_ids.add(issue_id)

        if line_no in seen_line_nos:
            apply_failures.append({"patch_id": patch_id, "error": "duplicate_line_no"})
            continue
        seen_line_nos.add(line_no)

        if line_no <= 0 or line_no > len(lines):
            apply_failures.append({"patch_id": patch_id, "error": "line_out_of_range"})
            continue

        current = lines[line_no - 1]
        if current != expected:
            apply_failures.append(
                {
                    "patch_id": patch_id,
                    "error": "expected_original_mismatch",
                    "line_no": line_no,
                }
            )
            continue

        lines[line_no - 1] = replacement
        applied.append({"patch_id": patch_id, "issue_id": issue_id, "line_no": line_no})

    if apply_failures:
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "input_markdown": str(input_markdown),
            "output_markdown": str(output_markdown),
            "snapshot_path": str(snapshot_path),
            "applied_count": len(applied),
            "failure_count": len(apply_failures),
            "applied": applied,
            "failures": apply_failures,
        }
        _write_json(report_path, report)
        raise SystemExit("Patch application failed. See apply report for details.")

    output_text = "\n".join(lines).rstrip() + "\n"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(input_text, encoding="utf-8")
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(output_text, encoding="utf-8")

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_markdown": str(input_markdown),
        "output_markdown": str(output_markdown),
        "snapshot_path": str(snapshot_path),
        "input_sha256": _sha256_text(input_text),
        "output_sha256": _sha256_text(output_text),
        "applied_count": len(applied),
        "failure_count": 0,
        "applied": applied,
        "failures": [],
    }
    _write_json(report_path, report)
    return report


def _as_object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
