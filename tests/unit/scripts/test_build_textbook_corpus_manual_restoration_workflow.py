"""Unit tests for textbook manual restoration workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.build_textbook_corpus_manual_restoration_workflow import (
    apply_patches,
    generate_packets,
    validate_patches,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def test_generate_packets_creates_unique_issue_ids_and_templates(tmp_path: Path) -> None:
    manual_queue = tmp_path / "manual-queue.jsonl"
    _write_jsonl(
        manual_queue,
        [
            {
                "code": "long_line_extreme",
                "line_no": 10,
                "severity": "high",
                "manual_required": True,
                "protected_zone": True,
                "message": "x",
                "line_text": "A",
            },
            {
                "code": "heading_artifact_dots",
                "line_no": 12,
                "severity": "medium",
                "manual_required": True,
                "protected_zone": False,
                "message": "y",
                "line_text": "B",
            },
        ],
    )

    output_dir = tmp_path / "workflow"
    report = generate_packets(
        manual_queue_path=manual_queue,
        output_dir=output_dir,
        packet_size=1,
        scaffold_patches=True,
    )

    assert report["issue_count"] == 2
    assert report["packet_count"] == 2
    assert (output_dir / "packets/PKT-0001.yaml").is_file()
    assert (output_dir / "packets/PKT-0002.yaml").is_file()
    assert len({item["issue_id"] for item in report["issues"]}) == 2

    patch_files = sorted((output_dir / "manual_fixes").glob("*.yaml"))
    assert len(patch_files) == 2


def test_validate_patches_rejects_self_approval(tmp_path: Path) -> None:
    patch_dir = tmp_path / "patches"
    patch_dir.mkdir(parents=True)
    patch_payload = {
        "version": 1,
        "patch_id": "PATCH-1",
        "issue_id": "ISSUE-1",
        "status": "approved",
        "author": "agent-a",
        "verifier": "agent-a",
        "verified_at": "2026-03-04T00:00:00Z",
        "rationale": "fix",
        "source": {"line_no": 2, "expected_original": "Old"},
        "change": {"mode": "replace_line", "replacement": "New"},
        "review": {"decision": "approved", "notes": ""},
    }
    (patch_dir / "patch.yaml").write_text(
        yaml.safe_dump(patch_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    report = validate_patches(
        patch_dir=patch_dir,
        report_path=tmp_path / "report.json",
    )

    assert report["summary"]["invalid_total"] == 1
    assert report["summary"]["valid_total"] == 0
    assert "self_approval_not_allowed" in report["results"][0]["errors"]


def test_apply_patches_is_deterministic_and_writes_snapshot(tmp_path: Path) -> None:
    markdown_path = tmp_path / "input.md"
    markdown_path.write_text("A\nB\nC\n", encoding="utf-8")

    patch_dir = tmp_path / "patches"
    patch_dir.mkdir(parents=True)
    patch_payload = {
        "version": 1,
        "patch_id": "PATCH-1",
        "issue_id": "ISSUE-1",
        "status": "approved",
        "author": "agent-a",
        "verifier": "agent-b",
        "verified_at": "2026-03-04T00:00:00Z",
        "rationale": "fix",
        "source": {"line_no": 2, "expected_original": "B"},
        "change": {"mode": "replace_line", "replacement": "B-fixed"},
        "review": {"decision": "approved", "notes": ""},
    }
    (patch_dir / "patch.yaml").write_text(
        yaml.safe_dump(patch_payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    output_one = tmp_path / "out-one.md"
    report_one = apply_patches(
        input_markdown=markdown_path,
        patch_dir=patch_dir,
        output_markdown=output_one,
        report_path=tmp_path / "apply-one.json",
        snapshot_path=tmp_path / "snapshot-one.md",
    )
    output_two = tmp_path / "out-two.md"
    report_two = apply_patches(
        input_markdown=markdown_path,
        patch_dir=patch_dir,
        output_markdown=output_two,
        report_path=tmp_path / "apply-two.json",
        snapshot_path=tmp_path / "snapshot-two.md",
    )

    assert output_one.read_text(encoding="utf-8") == "A\nB-fixed\nC\n"
    assert output_one.read_text(encoding="utf-8") == output_two.read_text(encoding="utf-8")
    assert report_one["output_sha256"] == report_two["output_sha256"]
    assert (tmp_path / "snapshot-one.md").read_text(encoding="utf-8") == "A\nB\nC\n"


def test_apply_patches_fails_on_duplicate_line_no(tmp_path: Path) -> None:
    markdown_path = tmp_path / "input.md"
    markdown_path.write_text("A\nB\nC\n", encoding="utf-8")
    patch_dir = tmp_path / "patches"
    patch_dir.mkdir(parents=True)

    first = {
        "version": 1,
        "patch_id": "PATCH-1",
        "issue_id": "ISSUE-1",
        "status": "approved",
        "author": "agent-a",
        "verifier": "agent-b",
        "verified_at": "2026-03-04T00:00:00Z",
        "rationale": "fix1",
        "source": {"line_no": 2, "expected_original": "B"},
        "change": {"mode": "replace_line", "replacement": "B-fixed"},
        "review": {"decision": "approved", "notes": ""},
    }
    second = {
        "version": 1,
        "patch_id": "PATCH-2",
        "issue_id": "ISSUE-2",
        "status": "approved",
        "author": "agent-c",
        "verifier": "agent-d",
        "verified_at": "2026-03-04T00:00:00Z",
        "rationale": "fix2",
        "source": {"line_no": 2, "expected_original": "B"},
        "change": {"mode": "replace_line", "replacement": "B-other"},
        "review": {"decision": "approved", "notes": ""},
    }

    (patch_dir / "patch-1.yaml").write_text(
        yaml.safe_dump(first, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (patch_dir / "patch-2.yaml").write_text(
        yaml.safe_dump(second, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        apply_patches(
            input_markdown=markdown_path,
            patch_dir=patch_dir,
            output_markdown=tmp_path / "out.md",
            report_path=tmp_path / "apply-report.json",
            snapshot_path=tmp_path / "snapshot.md",
        )
