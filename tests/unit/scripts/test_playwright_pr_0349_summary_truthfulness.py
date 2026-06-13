"""PR-0349 proof summary truthfulness tests.

Domain purpose:
    Protect the retained transcript parity proof summary from overstating
    blocked-run evidence or hiding typed Sir Convert trust blockers.

Relationships:
    Exercises the PR-0349 Playwright proof finalizer at the script/helper
    boundary without launching a browser.
"""

from __future__ import annotations

from pathlib import Path

from scripts._transcript_parity_evidence import NetworkRecord
from scripts.playwright_pr_0349_transcript_parity_live import (
    captured_artifact_summary,
    finalize_proof_summary,
)


def _internal_identity_record() -> NetworkRecord:
    return {
        "observed_at": "2026-06-13T13:43:45Z",
        "method": "POST",
        "path": "/sir-convert/v2/convert/jobs?wait_seconds=0",
        "status": 401,
        "content_type": "application/json",
        "scrubbed_payload": {
            "error_code": "auth_invalid_internal_identity",
            "message": "Missing or invalid signed internal identity context.",
            "retryable": False,
            "reason": "invalid_internal_identity_signature",
        },
    }


def test_blocked_summary_uses_typed_blocker_as_primary_failure(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "pr-0349"
    artifact_dir.mkdir()
    (artifact_dir / "downloads").mkdir()
    (artifact_dir / "failure.png").write_bytes(b"png")
    (artifact_dir / "network.bounded.json").write_text("[]\n", encoding="utf-8")
    (artifact_dir / "browser-console.bounded.json").write_text("[]\n", encoding="utf-8")
    summary: dict[str, object] = {
        "status": "failed",
        "failure": {
            "type": "TimeoutError",
            "message": 'Timeout 60000ms exceeded while waiting for event "response"',
        },
    }

    finalize_proof_summary(
        summary,
        artifact_dir=artifact_dir,
        network_records=[_internal_identity_record()],
    )

    failure = summary["failure"]
    assert isinstance(failure, dict)
    assert failure["type"] == "sir_convert_internal_identity_rejected"
    assert failure["kind"] == "sir_convert_internal_identity_rejected"
    assert failure["http_status"] == 401
    assert failure["error_code"] == "auth_invalid_internal_identity"
    assert failure["reason"] == "invalid_internal_identity_signature"
    assert failure["path"] == "/sir-convert/v2/convert/jobs?wait_seconds=0"
    assert summary["blocker_kind"] == "sir_convert_internal_identity_rejected"
    assert summary["blocker_error_code"] == "auth_invalid_internal_identity"
    raw_failure = summary["raw_failure"]
    assert isinstance(raw_failure, dict)
    assert raw_failure["type"] == "TimeoutError"


def test_captured_artifact_summary_lists_only_existing_evidence(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "pr-0349"
    artifact_dir.mkdir()
    (artifact_dir / "downloads").mkdir()
    (artifact_dir / "failure.png").write_bytes(b"png")
    (artifact_dir / "network.bounded.json").write_text("[]\n", encoding="utf-8")
    (artifact_dir / "browser-console.bounded.json").write_text("[]\n", encoding="utf-8")

    summary = captured_artifact_summary(artifact_dir)

    assert summary["screenshots"] == [str(artifact_dir / "failure.png")]
    assert summary["failure_screenshot"] == str(artifact_dir / "failure.png")
    assert summary["network"] == str(artifact_dir / "network.bounded.json")
    assert summary["console"] == str(artifact_dir / "browser-console.bounded.json")
    assert "cancel-accepted.png" not in str(summary)
    assert "progress.png" not in str(summary)
    assert "transcript-succeeded.png" not in str(summary)
    assert "replay-artifacts.png" not in str(summary)
    assert "complete.png" not in str(summary)
