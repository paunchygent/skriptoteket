"""Unit tests for textbook corpus baseline snapshot and reconciliation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_textbook_corpus_baseline import build_baseline


class FakeServiceClient:
    """Simple fake service client used for reconciliation tests."""

    def __init__(self) -> None:
        self.job_calls: list[str] = []
        self.result_calls: list[str] = []
        self.artifact_calls: list[str] = []

    def get_job(self, job_id: str) -> dict[str, Any]:
        self.job_calls.append(job_id)
        return {
            "api_version": "v2",
            "job": {
                "job_id": job_id,
                "status": "succeeded",
            },
        }

    def get_result(self, job_id: str) -> dict[str, Any]:
        self.result_calls.append(job_id)
        return {
            "api_version": "v2",
            "job_id": job_id,
            "status": "succeeded",
            "result": {
                "artifact": {
                    "filename": "output.md",
                    "format": "md",
                }
            },
        }

    def fetch_artifact(self, job_id: str) -> bytes:
        self.artifact_calls.append(job_id)
        return b"# fetched\n"


def test_build_baseline_copies_manifest_sources_and_local_outputs(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "baseline"
    source_dir.mkdir(parents=True)

    source_file = source_dir / "book_source.pdf"
    source_file.write_bytes(b"%PDF-1.7 baseline\n")
    local_output = source_dir / "book.md"
    local_output.write_text("hello world\n", encoding="utf-8")

    manifest = {
        "api_version": "v1",
        "source_root": str(source_file),
        "entries": [
            {
                "job_id": "jobv2_abc",
                "source_file_path": source_file.name,
                "output_path": str(local_output),
                "status": "succeeded",
                "error_code": None,
                "pipeline_used": "service: pdf -> md (v2)",
                "source_format": "pdf",
                "target_format": "md",
            }
        ],
    }
    (source_dir / "sir_convert_a_lot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload = build_baseline(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest_glob="sir_convert_a_lot_manifest*.json",
        service_client=None,
        fetch_missing_artifacts=True,
        dry_run=False,
    )

    assert (output_dir / "raw/manifests/sir_convert_a_lot_manifest.json").is_file()
    assert (output_dir / "raw/sources/sir_convert_a_lot_manifest.json/book_source.pdf").is_file()
    assert (output_dir / "raw/outputs/local/jobv2_abc__book.md").is_file()
    assert (output_dir / "checksums.json").is_file()
    assert (output_dir / "provenance/reconciliation-report.json").is_file()

    summary = payload["report"]["summary"]
    assert summary["status_succeeded"] == 1
    assert summary["local_output_exists"] == 1
    assert summary["fetched_artifact_count"] == 0


def test_build_baseline_reconciles_timeout_job_and_fetches_artifact(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "baseline"
    source_dir.mkdir(parents=True)

    source_file = source_dir / "syntes.pdf"
    source_file.write_bytes(b"%PDF-1.7\n")
    missing_output = source_dir / "syntes.md"

    manifest = {
        "api_version": "v1",
        "source_root": str(source_file),
        "entries": [
            {
                "job_id": "jobv2_timeout",
                "source_file_path": source_file.name,
                "output_path": str(missing_output),
                "status": "running",
                "error_code": "job_timeout",
                "pipeline_used": "service: pdf -> md (v2)",
                "source_format": "pdf",
                "target_format": "md",
            }
        ],
    }
    (source_dir / "sir_convert_a_lot_manifest_full_ocr.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fake_client = FakeServiceClient()
    payload = build_baseline(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest_glob="sir_convert_a_lot_manifest*.json",
        service_client=fake_client,
        fetch_missing_artifacts=True,
        dry_run=False,
    )

    assert fake_client.job_calls == ["jobv2_timeout"]
    assert fake_client.result_calls == ["jobv2_timeout"]
    assert fake_client.artifact_calls == ["jobv2_timeout"]

    assert (output_dir / "provenance/jobs/jobv2_timeout.job.json").is_file()
    assert (output_dir / "provenance/jobs/jobv2_timeout.result.json").is_file()
    assert (output_dir / "raw/outputs/fetched/jobv2_timeout.md").is_file()

    row = payload["report"]["reconciliation_rows"][0]
    assert row["status_reconciled"] == "succeeded"
    assert row["fetched_artifact_snapshot_path"] == "raw/outputs/fetched/jobv2_timeout.md"
    assert row["issues"] == []


def test_build_baseline_marks_reconciliation_skipped_without_service_client(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "baseline"
    source_dir.mkdir(parents=True)

    source_file = source_dir / "syntes.pdf"
    source_file.write_bytes(b"%PDF-1.7\n")
    missing_output = source_dir / "syntes.md"

    manifest = {
        "api_version": "v1",
        "source_root": str(source_file),
        "entries": [
            {
                "job_id": "jobv2_noauth",
                "source_file_path": source_file.name,
                "output_path": str(missing_output),
                "status": "running",
                "error_code": "job_poll_window_exceeded",
                "pipeline_used": "service: pdf -> md (v2)",
                "source_format": "pdf",
                "target_format": "md",
            }
        ],
    }
    (source_dir / "sir_convert_a_lot_manifest_full_ocr.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload = build_baseline(
        source_dir=source_dir,
        output_dir=output_dir,
        manifest_glob="sir_convert_a_lot_manifest*.json",
        service_client=None,
        fetch_missing_artifacts=True,
        dry_run=False,
    )

    row = payload["report"]["reconciliation_rows"][0]
    assert "reconciliation_skipped_missing_api_key" in row["issues"]
    assert row["fetched_artifact_snapshot_path"] is None
