"""Audio Transcription retryable reattempt proof tests.

Domain purpose:
    Protect the reusable public browser proof for Service API v2
    retryable-failed idempotency reattempts.

Relationships:
    Exercises Skriptoteket-owned Gateway evidence helpers without browser,
    HuleEdu, or Sir Convert runtime mutation.
"""

from __future__ import annotations

from scripts._sir_convert_gateway_evidence import (
    GatewayCapture,
    assert_retryable_reattempt_evidence,
)
from scripts.audio_transcription_retryable_reattempt_public_proof import PROOF_KIND


def _capture_with_service_reattempt() -> GatewayCapture:
    capture = GatewayCapture()
    capture.request_records.extend(
        [
            {
                "phase": "replay",
                "observed_at": "2026-06-29T08:22:27Z",
                "method": "POST",
                "path": "/sir-convert/v2/convert/jobs?wait_seconds=0",
                "headers": {"idempotency-key": "idem_same"},
            }
        ]
    )
    capture.response_records.extend(
        [
            {
                "phase": "replay",
                "observed_at": "2026-06-29T08:22:27Z",
                "method": "POST",
                "path": "/sir-convert/v2/convert/jobs?wait_seconds=0",
                "status": 202,
                "payload": {
                    "job": {
                        "job_id": "jobv2_new",
                        "status": "queued",
                        "source_format": "audio",
                        "output_format": "transcript_bundle",
                    },
                    "idempotency": {
                        "state": "service_reattempt",
                        "idempotent_replay": False,
                        "active_job_id": "jobv2_new",
                        "attempt_count": 2,
                        "previous_attempts": [
                            {
                                "job_id": "jobv2_failed",
                                "status": "failed",
                                "failure_retryable": True,
                            }
                        ],
                        "reattempt_of_job_id": "jobv2_failed",
                    },
                },
            },
            {
                "phase": "replay",
                "observed_at": "2026-06-29T08:23:16Z",
                "method": "GET",
                "path": "/sir-convert/v2/convert/jobs/jobv2_new/result",
                "status": 200,
                "payload": {"result": {"artifact": {"format": "transcript_bundle"}}},
            },
            {
                "phase": "replay",
                "observed_at": "2026-06-29T08:23:16Z",
                "method": "GET",
                "path": "/sir-convert/v2/convert/jobs/jobv2_new/artifacts",
                "status": 200,
                "payload": {"artifacts": [{"artifact_key": "transcript_json"}]},
            },
            {
                "phase": "replay",
                "observed_at": "2026-06-29T08:23:16Z",
                "method": "GET",
                "path": "/sir-convert/v2/convert/jobs/jobv2_new/artifacts/transcript_json",
                "status": 200,
                "payload": {
                    "transcript_json": {
                        "schema_version": "transcript_json_v1",
                        "segment_count": 1,
                        "speaker_label_count": 1,
                        "language_detected": "sv",
                        "diarization_status": "succeeded",
                        "text_present": True,
                    }
                },
            },
        ]
    )
    return capture


def test_retryable_reattempt_proof_uses_domain_kind() -> None:
    assert PROOF_KIND == "audio_transcription_retryable_reattempt_public"
    assert not PROOF_KIND.startswith("task_")
    assert not PROOF_KIND.startswith("playwright_pr_")


def test_retryable_reattempt_evidence_requires_one_replay_submit_and_lineage() -> None:
    summary = assert_retryable_reattempt_evidence(
        capture=_capture_with_service_reattempt(),
        precondition_job_id="jobv2_failed",
        precondition_idempotency_key="idem_same",
    )

    assert summary["replay_create_post_count"] == 1
    assert summary["same_idempotency_key_as_precondition"] is True
    assert summary["replay_job_id"] == "jobv2_new"
    assert summary["service_reattempt"] == {
        "state": "service_reattempt",
        "attempt_count": 2,
        "active_job_id": "jobv2_new",
        "reattempt_of_job_id": "jobv2_failed",
        "previous_attempts": [
            {
                "job_id": "jobv2_failed",
                "status": "failed",
                "failure_retryable": True,
            }
        ],
    }
    assert summary["artifact_fetches"]["transcript_json_fetch_status"] == 200


def test_retryable_reattempt_evidence_rejects_extra_replay_submit() -> None:
    capture = _capture_with_service_reattempt()
    capture.request_records.append(
        {
            "phase": "replay",
            "observed_at": "2026-06-29T08:22:28Z",
            "method": "POST",
            "path": "/sir-convert/v2/convert/jobs?wait_seconds=0",
            "headers": {"idempotency-key": "idem_same"},
        }
    )

    try:
        assert_retryable_reattempt_evidence(
            capture=capture,
            precondition_job_id="jobv2_failed",
            precondition_idempotency_key="idem_same",
        )
    except AssertionError as exc:
        assert "Replay emitted 2 create-job POSTs" in str(exc)
    else:
        raise AssertionError("Expected duplicate replay submission to fail.")
