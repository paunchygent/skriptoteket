"""Story 58 private request capture helper tests.

Domain purpose:
    Prove the Story 58 closeout harness can retain raw Sir Convert correction
    request bodies out-of-band while exposing only approved public metadata.

Relationships:
    - Exercises `scripts._story58_private_request_capture`.
    - Protects `scripts.playwright_pr_0337_correction_session_live` from
      leaking private request material into retained browser-proof artifacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import playwright_pr_0337_correction_session_live as correction_live
from scripts._story58_mismatched_artifact_probe import (
    assert_mismatched_artifact_probe_fail_closed,
    mismatched_artifact_download_probe_summary,
    mismatched_artifact_download_request,
)
from scripts._story58_private_request_capture import Story58PrivateRequestCapture


class FakeRequest:
    """Minimal Playwright request double for request-capture unit tests."""

    def __init__(self, *, method: str, url: str, post_data: str | None) -> None:
        self.method = method
        self.url = url
        self.post_data = post_data


class FakeResponse:
    """Minimal Playwright response double for PR-0337 summary tests."""

    def __init__(
        self,
        *,
        content_type: str = "application/json",
        method: str = "GET",
        payload: dict[str, object] | None = None,
        status: int,
        url: str,
    ) -> None:
        self.headers = {"content-type": content_type}
        self.request = FakeRequest(method=method, url=url, post_data=None)
        self.status = status
        self.url = url
        self._payload = payload or {}

    def json(self) -> dict[str, object]:
        return self._payload


class FakeFailureArtifactPage:
    """Page double whose failure-artifact captures fail after an original error."""

    url = "chrome-error://chromewebdata/"

    def screenshot(self, **_kwargs: object) -> None:
        raise TimeoutError("screenshot timed out")

    def title(self) -> str:
        raise RuntimeError("title capture failed")


def test_capture_writes_raw_body_privately_and_public_summary_is_redacted(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": "exam_authoring_correction_apply_request_v1",
        "request_id": "req-123",
        "job_id": "job-abc",
        "source_binding": {
            "source_bundle_id": "bundle-1",
            "source_file_sha256": "file-digest",
            "source_state_sha256": "state-digest",
            "source_state_signature": "must-not-retain-signature",
        },
        "requested_targets": ["pdf", "qti"],
        "idempotency_key": "must-not-retain-idempotency",
        "identity_context": {"subject": "must-not-retain-identity"},
        "public_conversion_grant": "must-not-retain-grant",
        "provider_prompt": "must-not-retain-prompt",
        "corrections": [
            {
                "entry_id": "entry-1",
                "kind": "answer_key",
                "source_text": "must-not-retain-source-text",
            }
        ],
    }
    raw_body = json.dumps(payload, ensure_ascii=False)
    capture = Story58PrivateRequestCapture(private_dir=tmp_path / "private")

    capture.handle_request(
        FakeRequest(
            method="POST",
            url="https://api.hule.education/sir-convert/v2/exam-authoring/corrections/apply",
            post_data=raw_body,
        )
    )

    private_manifest = json.loads((tmp_path / "private" / "manifest.json").read_text())
    private_body_path = tmp_path / "private" / private_manifest["captures"][0]["filename"]
    assert private_body_path.read_text(encoding="utf-8") == raw_body

    public_summary = capture.public_summary()
    rendered_public_summary = json.dumps(public_summary, ensure_ascii=False)
    assert public_summary["enabled"] is True
    assert public_summary["request_count"] == 1
    assert public_summary["private_paths_retained"] is False
    assert public_summary["raw_bodies_retained"] is False
    assert public_summary["private_capture_location"] == "private_capture_dir_only"
    assert public_summary["counts"] == {
        "correction_apply": 1,
        "source_state_issue": 0,
    }
    assert public_summary["captures"][0] == {
        "body_sha256": hashlib.sha256(raw_body.encode("utf-8")).hexdigest(),
        "correction_count": 1,
        "corrections_sha256": hashlib.sha256(
            json.dumps(payload["corrections"], ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "job_id": "job-abc",
        "kind": "correction_apply",
        "method": "POST",
        "path": "/sir-convert/v2/exam-authoring/corrections/apply",
        "request_id": "req-123",
        "requested_target_count": 2,
        "requested_targets": ["pdf", "qti"],
        "schema_version": "exam_authoring_correction_apply_request_v1",
        "source_bundle_id": "bundle-1",
        "source_file_sha256": "file-digest",
        "source_state_sha256": "state-digest",
    }
    assert str(private_body_path) not in rendered_public_summary
    assert "must-not-retain" not in rendered_public_summary
    assert "source_state_signature" not in rendered_public_summary
    assert "raw_body" not in rendered_public_summary


def test_capture_records_source_state_issue_metadata_without_source_state_body(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
        "request_id": "req-source-state",
        "source_bundle_id": "bundle-top-level",
        "source_file_sha256": "file-top-level",
        "source_state_sha256": "state-top-level",
        "source_authoring_state": {
            "items": [
                {"source_text": "must-not-retain-item-1"},
                {"source_text": "must-not-retain-item-2"},
            ]
        },
    }
    raw_body = json.dumps(payload, ensure_ascii=False)
    capture = Story58PrivateRequestCapture(private_dir=tmp_path / "private")

    capture.handle_request(
        FakeRequest(
            method="POST",
            url=(
                "https://api.hule.education/sir-convert/v2/exam-authoring/"
                "corrections/source-state/issue"
            ),
            post_data=raw_body,
        )
    )

    public_entry = capture.public_summary()["captures"][0]
    assert public_entry == {
        "body_sha256": hashlib.sha256(raw_body.encode("utf-8")).hexdigest(),
        "kind": "source_state_issue",
        "method": "POST",
        "path": "/sir-convert/v2/exam-authoring/corrections/source-state/issue",
        "request_id": "req-source-state",
        "schema_version": "exam_authoring_correction_source_state_issue_request_v1",
        "source_bundle_id": "bundle-top-level",
        "source_file_sha256": "file-top-level",
        "source_state_item_count": 2,
        "source_state_sha256": "state-top-level",
    }
    assert "must-not-retain" not in json.dumps(public_entry, ensure_ascii=False)


def test_capture_ignores_non_target_requests(tmp_path: Path) -> None:
    capture = Story58PrivateRequestCapture(private_dir=tmp_path / "private")

    capture.handle_request(
        FakeRequest(
            method="GET",
            url="https://api.hule.education/sir-convert/v2/exam-authoring/corrections/apply",
            post_data=None,
        )
    )
    capture.handle_request(
        FakeRequest(
            method="POST",
            url="https://api.hule.education/sir-convert/v2/convert/jobs",
            post_data="{}",
        )
    )

    assert capture.public_summary()["request_count"] == 0
    assert not (tmp_path / "private" / "manifest.json").exists()


def test_capture_rejects_private_dir_inside_retained_artifact_dir(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="private capture directory"):
        Story58PrivateRequestCapture(
            private_dir=tmp_path / "artifacts" / "private",
            retained_artifact_dir=tmp_path / "artifacts",
        )


def test_pr_0337_cli_registers_opt_in_private_capture_dir() -> None:
    args = correction_live._parse_args(
        [
            "--story58-private-request-capture-dir",
            "private-story58-captures",
        ]
    )

    assert args.story58_private_request_capture_dir == Path("private-story58-captures")


def test_pr_0337_request_handler_preserves_apply_summary_and_capture(
    tmp_path: Path,
) -> None:
    payload: dict[str, object] = {
        "schema_version": "exam_authoring_correction_apply_request_v1",
        "corrections": [
            {
                "entry_id": "entry-1",
                "item_id": "item-1",
                "kind": "answer_key",
                "sequence": 7,
                "source_text": "must-not-retain-source-text",
                "teacher_answer": "must-not-retain-answer-text",
            }
        ],
        "request_id": "req-apply",
        "requested_targets": ["pdf"],
        "source_binding": {"source_state_sha256": "state-digest"},
    }
    correction_apply_requests: list[dict[str, object]] = []
    summary: dict[str, object] = {"correction_apply_requests": correction_apply_requests}
    capture = Story58PrivateRequestCapture(private_dir=tmp_path / "private")

    correction_live._handle_request(
        FakeRequest(
            method="POST",
            url="https://api.hule.education/sir-convert/v2/exam-authoring/corrections/apply",
            post_data=json.dumps(payload),
        ),
        summary=summary,
        story58_capture=capture,
    )

    assert correction_apply_requests[0]["correction_count"] == 1
    assert correction_apply_requests[0]["requested_targets"] == ["pdf"]
    rendered_apply_summary = json.dumps(correction_apply_requests, ensure_ascii=False)
    assert "corrections" not in correction_apply_requests[0]
    assert "entry_id" not in rendered_apply_summary
    assert "item_id" not in rendered_apply_summary
    assert "kind" not in rendered_apply_summary
    assert "sequence" not in rendered_apply_summary
    assert "must-not-retain" not in rendered_apply_summary
    assert capture.public_summary()["request_count"] == 1


def test_pr_0337_response_summary_retains_safe_correction_replay_references() -> None:
    response = FakeResponse(
        method="POST",
        status=200,
        url="https://api.hule.education/sir-convert/v2/exam-authoring/corrections/apply",
        payload={
            "schema_version": "exam_authoring_correction_apply_response_v1",
            "request_id": "req-apply",
            "correction_replay_artifact_references": [
                {
                    "schema_version": "correction_replay_artifact_reference_v1",
                    "job_id": "must-not-retain-job",
                    "artifact_set_id": "crset-real",
                    "artifact_key": "correction_replay_examnet_pdf",
                    "target": "examnet_pdf",
                    "content_sha256": "sha256:original",
                    "request_id": "req-ref",
                    "source_binding_digest": "sha256:source-binding",
                    "source_state_sha256": "sha256:source-state",
                    "correction_payload_digest": "sha256:correction-payload",
                    "target_set_digest": "sha256:target-set",
                    "created_at": "must-not-retain-created-at",
                    "replay_profile_version": "must-not-retain-profile",
                    "source_text": "must-not-retain-source-text",
                }
            ],
        },
    )

    summary = correction_live._summarize_response(response)

    assert summary["json"]["correction_replay_artifact_references"] == [
        {
            "schema_version": "correction_replay_artifact_reference_v1",
            "job_id": "must-not-retain-job",
            "artifact_set_id": "crset-real",
            "artifact_key": "correction_replay_examnet_pdf",
            "content_sha256": "sha256:original",
            "request_id": "req-ref",
            "source_binding_digest": "sha256:source-binding",
            "source_state_sha256": "sha256:source-state",
            "correction_payload_digest": "sha256:correction-payload",
            "target_set_digest": "sha256:target-set",
        }
    ]
    rendered = json.dumps(summary, ensure_ascii=False)
    assert "must-not-retain-created-at" not in rendered
    assert "must-not-retain-profile" not in rendered
    assert "must-not-retain-source-text" not in rendered
    assert "source_text" not in rendered


def test_pr_0337_failure_artifacts_do_not_mask_original_exception_metadata(
    tmp_path: Path,
) -> None:
    summary: dict[str, object] = {"screenshots": []}
    original = AssertionError("login failed before upload")

    correction_live._record_failure_artifacts(
        FakeFailureArtifactPage(),
        artifact_dir=tmp_path,
        original_exception=original,
        summary=summary,
    )

    assert summary["failure"] == {
        "exception_type": "AssertionError",
        "message": "login failed before upload",
    }
    assert summary["screenshots"] == []
    assert summary["failure_artifact_errors"] == [
        {
            "artifact": "screenshot",
            "exception_type": "TimeoutError",
            "message": "screenshot timed out",
        },
        {
            "artifact": "failure_text",
            "exception_type": "RuntimeError",
            "message": "title capture failed",
        },
    ]
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["failure"]["exception_type"] == "AssertionError"


def test_pr_0337_final_summary_write_failure_does_not_mask_active_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    summary: dict[str, object] = {}
    original = AssertionError("conversion failed before replay")

    def fail_summary(_summary: dict[str, object], _artifact_dir: Path) -> None:
        raise OSError("manifest writer unavailable")

    monkeypatch.setattr(correction_live, "_write_summary", fail_summary)

    with pytest.raises(AssertionError, match="conversion failed before replay") as raised:
        try:
            raise original
        except AssertionError as exc:
            correction_live._write_final_summary(
                summary,
                tmp_path,
                active_exception=exc,
            )
            raise

    assert raised.value is original
    assert summary.get("failure_artifact_errors") == [
        {
            "artifact": "final_summary",
            "exception_type": "OSError",
            "message": "manifest writer unavailable",
        }
    ]


def test_pr_0337_mismatched_artifact_probe_corrupts_only_content_hash() -> None:
    evidence = {
        "path": (
            "/sir-convert/v2/convert/jobs/jobv2_real/correction-replays/crset-real/"
            "artifacts/correction_replay_examnet_pdf?content_sha256=sha256:abc123"
        ),
        "replay_artifact_key": "correction_replay_examnet_pdf",
        "replay_artifact_set_id": "crset-real",
        "content_sha256": "sha256:abc123",
    }

    probe = mismatched_artifact_download_request(evidence)

    assert probe["artifact_key"] == "correction_replay_examnet_pdf"
    assert probe["artifact_set_id"] == "crset-real"
    assert probe["original_content_sha256"] == "sha256:abc123"
    assert probe["mismatched_content_sha256"] != "sha256:abc123"
    assert probe["path"].startswith(
        "/sir-convert/v2/convert/jobs/jobv2_real/correction-replays/crset-real/"
        "artifacts/correction_replay_examnet_pdf?"
    )
    assert "content_sha256=sha256%3Aabc123" not in probe["path"]
    assert probe["path"].count("content_sha256=") == 1


def test_pr_0337_mismatched_artifact_probe_summary_is_fail_closed_and_redacted() -> None:
    response = FakeResponse(
        status=409,
        url=(
            "https://api.hule.education/sir-convert/v2/convert/jobs/jobv2_real/"
            "correction-replays/crset-real/artifacts/correction_replay_examnet_pdf"
            "?content_sha256=sha256:mismatch"
        ),
        payload={
            "error": {
                "code": "correction_replay_artifact_reference_mismatch",
                "message": "must-not-retain-message",
                "details": {"private_path": "must-not-retain-path"},
            }
        },
    )
    request = {
        "artifact_key": "correction_replay_examnet_pdf",
        "artifact_set_id": "crset-real",
        "mismatched_content_sha256": "sha256:mismatch",
        "original_content_sha256": "sha256:original",
        "path": (
            "/sir-convert/v2/convert/jobs/jobv2_real/correction-replays/crset-real/"
            "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Amismatch"
        ),
    }

    summary = mismatched_artifact_download_probe_summary(
        response,
        request=request,
    )

    assert_mismatched_artifact_probe_fail_closed(summary)
    assert summary == {
        "artifact_key": "correction_replay_examnet_pdf",
        "artifact_set_id": "crset-real",
        "error_code": "correction_replay_artifact_reference_mismatch",
        "mismatched_content_sha256": "sha256:mismatch",
        "original_content_sha256": "sha256:original",
        "path": (
            "/sir-convert/v2/convert/jobs/jobv2_real/correction-replays/crset-real/"
            "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Amismatch"
        ),
        "status": 409,
    }
    assert "must-not-retain" not in json.dumps(summary, ensure_ascii=False)
