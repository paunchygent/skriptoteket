"""Story 58 artifact route probe helper tests.

Domain purpose:
    Prove the proof harness observes correction replay artifact routes through
    approved product/Gateway metadata without retaining private correction
    request or response material.

Relationships:
    - Exercises `scripts._story58_artifact_route_probe`.
    - Complements invariant tests by proving how route observations are bound
      to redacted correction request digests.
"""

from __future__ import annotations

import json
from typing import TypedDict

from scripts._story58_artifact_route_probe import (
    probe_safe_correction_replay_artifacts,
    story58_latest_correction_request_context,
    story58_snapshot_evidence_with_request_context,
)
from scripts._story58_artifact_set_invariants import record_story58_artifact_set_snapshot


class Story58ArtifactSnapshot(TypedDict, total=False):
    """Typed approved metadata retained for one route-observed artifact."""

    artifact_key: str
    artifact_set_id: str
    content_sha256: str
    corrections_sha256: str
    job_id: str
    observed_via: str
    path: str
    product_route_observed: bool
    request_digest: str
    request_id: str
    request_occurrence: int
    status: int
    ui_artifact_key: str


class FakeRouteResponse:
    """Minimal response double for Story 58 route-probe tests."""

    def __init__(self, *, status: int) -> None:
        self.status = status


class FakeRouteRequestContext:
    """Request-context double that records product-route proof GETs."""

    def __init__(self, *, status: int = 200) -> None:
        self.status = status
        self.get_calls: list[dict[str, object]] = []

    def get(self, url: str, *, timeout: float | None = None) -> FakeRouteResponse:
        self.get_calls.append({"timeout": timeout, "url": url})
        return FakeRouteResponse(status=self.status)


def test_latest_request_context_marks_product_route_snapshot_without_raw_request_data() -> None:
    snapshots: list[Story58ArtifactSnapshot] = []
    summary: dict[str, object] = {
        "correction_apply_requests": [
            {
                "body_sha256": "sha256:body-baseline",
                "corrections_sha256": "sha256:corrections-baseline",
                "idempotency_key": "must-not-retain",
                "raw_body": "must-not-retain",
                "request_id": "req-baseline",
                "source_text": "must-not-retain",
            }
        ],
        "story58_artifact_set_snapshots": snapshots,
    }

    context = story58_latest_correction_request_context(summary)
    evidence = story58_snapshot_evidence_with_request_context(
        {
            "content_sha256": "sha256:content-baseline",
            "path": (
                "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-baseline/"
                "artifacts/correction_replay_examnet_pdf"
                "?content_sha256=sha256%3Acontent-baseline"
            ),
            "replay_artifact_key": "correction_replay_examnet_pdf",
            "replay_artifact_set_id": "crset-baseline",
            "status": 200,
            "ui_artifact_key": "examnet_pdf",
        },
        context,
    )

    record_story58_artifact_set_snapshot(
        summary,
        evidence,
        observed_via="exportable-baseline-download",
    )

    rendered = json.dumps(snapshots, ensure_ascii=False)
    assert "must-not-retain" not in rendered
    assert snapshots[0]["request_digest"] == ("sha256:body-baseline")
    assert snapshots[0]["request_id"] == "req-baseline"
    assert snapshots[0]["request_occurrence"] == 1


def test_reference_probe_uses_nested_route_and_retains_only_approved_metadata() -> None:
    request_context = FakeRouteRequestContext()
    snapshots: list[Story58ArtifactSnapshot] = []
    summary: dict[str, object] = {
        "correction_apply_requests": [
            {
                "body_sha256": "sha256:body-final",
                "corrections_sha256": "sha256:corrections-final",
                "request_id": "req-final",
            }
        ],
        "correction_apply_responses": [
            {
                "json": {
                    "request_id": "req-final",
                    "correction_replay_artifact_references": [
                        {
                            "schema_version": "correction_replay_artifact_reference_v1",
                            "artifact_set_id": "crset-final",
                            "artifact_key": "correction_replay_examnet_pdf",
                            "content_sha256": "sha256:content-final",
                            "job_id": "jobv2-final",
                            "source_text": "must-not-retain",
                        }
                    ],
                }
            }
        ],
        "story58_artifact_set_snapshots": snapshots,
    }

    result = probe_safe_correction_replay_artifacts(
        request_context,
        api_base_url="https://api.hule.education",
        summary=summary,
    )

    assert result == {
        "attempted_count": 1,
        "skipped_count": 0,
    }
    assert request_context.get_calls == [
        {
            "timeout": 30_000,
            "url": (
                "https://api.hule.education/sir-convert/v2/convert/jobs/jobv2-final/"
                "correction-replays/crset-final/artifacts/correction_replay_examnet_pdf"
                "?content_sha256=sha256%3Acontent-final"
            ),
        }
    ]
    snapshot = snapshots[0]
    assert snapshot == {
        "artifact_key": "correction_replay_examnet_pdf",
        "artifact_set_id": "crset-final",
        "content_sha256": "sha256:content-final",
        "corrections_sha256": "sha256:corrections-final",
        "job_id": "jobv2-final",
        "observed_via": "apply-response-reference",
        "path": (
            "/sir-convert/v2/convert/jobs/jobv2-final/correction-replays/crset-final/"
            "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-final"
        ),
        "product_route_observed": True,
        "request_digest": "sha256:body-final",
        "request_id": "req-final",
        "request_occurrence": 1,
        "status": 200,
    }
    assert "must-not-retain" not in json.dumps(
        summary["story58_artifact_set_snapshots"],
        ensure_ascii=False,
    )


def test_reference_probe_fails_when_attempted_nested_route_is_not_2xx() -> None:
    request_context = FakeRouteRequestContext(status=409)
    snapshots: list[Story58ArtifactSnapshot] = []
    summary: dict[str, object] = {
        "correction_apply_requests": [{"body_sha256": "sha256:body", "request_id": "req"}],
        "correction_apply_responses": [
            {
                "json": {
                    "request_id": "req",
                    "correction_replay_artifact_references": [
                        {
                            "schema_version": "correction_replay_artifact_reference_v1",
                            "artifact_set_id": "crset-failed",
                            "artifact_key": "correction_replay_examnet_pdf",
                            "content_sha256": "sha256:content-failed",
                            "job_id": "jobv2-failed",
                        }
                    ],
                }
            }
        ],
        "story58_artifact_set_snapshots": snapshots,
    }

    try:
        probe_safe_correction_replay_artifacts(
            request_context,
            api_base_url="https://api.hule.education",
            summary=summary,
        )
    except AssertionError as exc:
        assert "HTTP 409" in str(exc)
    else:  # pragma: no cover - assertion clarity.
        raise AssertionError("Expected non-2xx nested route probe to fail.")
