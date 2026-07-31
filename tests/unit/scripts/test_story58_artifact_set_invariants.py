"""Story 58 artifact-set invariant helper tests.

Domain purpose:
    Prove the public Story 58 proof harness can classify correction request
    digest to replay artifact-set invariants without retaining private request
    bodies or source material.

Relationships:
    - Exercises `scripts._story58_artifact_set_invariants`.
    - Protects `scripts.playwright_pr_0337_correction_session_live` from
      claiming Story 58 duplicate/distinct replay proof from final downloads
      alone.
"""

from __future__ import annotations

import json
from typing import TypedDict, TypeGuard

from scripts._story58_artifact_set_invariants import (
    record_story58_artifact_set_snapshot,
    summarize_artifact_set_invariants,
    summarize_manifest_artifact_set_invariants,
)


class _InvariantSummary(TypedDict):
    status: str
    paired_observation_count: int


def _is_invariant_summary(value: object) -> TypeGuard[_InvariantSummary]:
    return (
        isinstance(value, dict)
        and isinstance(value.get("status"), str)
        and isinstance(value.get("paired_observation_count"), int)
    )


def _observation(
    *,
    artifact_set_id: str,
    request_digest: str,
    request_occurrence: int,
) -> dict[str, object]:
    return {
        "artifact_key": "correction_replay_examnet_pdf",
        "artifact_set_id": artifact_set_id,
        "content_sha256": f"sha256:content-{artifact_set_id}",
        "corrections_sha256": f"sha256:corrections-{request_digest}",
        "path": (
            "/sir-convert/v2/convert/jobs/job-1/correction-replays/"
            f"{artifact_set_id}/artifacts/correction_replay_examnet_pdf"
            f"?content_sha256=sha256%3Acontent-{artifact_set_id}"
        ),
        "product_route_observed": True,
        "request_digest": request_digest,
        "request_id": f"req-{request_occurrence}",
        "request_occurrence": request_occurrence,
        "status": 200,
    }


def test_duplicate_request_digest_with_same_replay_artifact_set_passes() -> None:
    summary = summarize_artifact_set_invariants(
        [
            _observation(
                artifact_set_id="crset-final",
                request_digest="sha256:final-v10",
                request_occurrence=1,
            ),
            _observation(
                artifact_set_id="crset-final",
                request_digest="sha256:final-v10",
                request_occurrence=2,
            ),
        ]
    )

    assert summary["status"] == "pass"
    duplicate_row = summary["rows"][0]
    assert duplicate_row["invariant"] == "duplicate_request_digest_same_artifact_set"
    assert duplicate_row["status"] == "pass"
    assert duplicate_row["request_digest"] == "sha256:final-v10"
    assert duplicate_row["artifact_set_ids"] == ["crset-final"]


def test_distinct_request_digests_with_distinct_replay_artifact_sets_passes() -> None:
    summary = summarize_artifact_set_invariants(
        [
            _observation(
                artifact_set_id="crset-first",
                request_digest="sha256:correction-a",
                request_occurrence=1,
            ),
            _observation(
                artifact_set_id="crset-second",
                request_digest="sha256:correction-b",
                request_occurrence=2,
            ),
        ]
    )

    assert summary["status"] == "pass"
    distinct_row = summary["rows"][1]
    assert distinct_row["invariant"] == "distinct_request_digests_distinct_artifact_sets"
    assert distinct_row["status"] == "pass"
    assert distinct_row["request_digests"] == ["sha256:correction-a", "sha256:correction-b"]
    assert distinct_row["artifact_set_ids"] == ["crset-first", "crset-second"]


def test_duplicate_request_digest_with_changed_replay_artifact_set_fails() -> None:
    summary = summarize_artifact_set_invariants(
        [
            _observation(
                artifact_set_id="crset-first",
                request_digest="sha256:final-v10",
                request_occurrence=1,
            ),
            _observation(
                artifact_set_id="crset-second",
                request_digest="sha256:final-v10",
                request_occurrence=2,
            ),
        ]
    )

    assert summary["status"] == "fail"
    duplicate_row = summary["rows"][0]
    assert duplicate_row["status"] == "fail"
    assert duplicate_row["artifact_set_ids"] == ["crset-first", "crset-second"]


def test_distinct_request_digests_with_same_replay_artifact_set_fails() -> None:
    summary = summarize_artifact_set_invariants(
        [
            _observation(
                artifact_set_id="crset-reused",
                request_digest="sha256:correction-a",
                request_occurrence=1,
            ),
            _observation(
                artifact_set_id="crset-reused",
                request_digest="sha256:correction-b",
                request_occurrence=2,
            ),
        ]
    )

    assert summary["status"] == "fail"
    distinct_row = summary["rows"][1]
    assert distinct_row["status"] == "fail"
    assert distinct_row["artifact_set_ids"] == ["crset-reused"]


def test_final_download_only_leaves_duplicate_and_distinct_rows_unproven() -> None:
    summary = summarize_artifact_set_invariants(
        [
            _observation(
                artifact_set_id="crset-final",
                request_digest="sha256:final-v10",
                request_occurrence=1,
            )
        ]
    )

    assert summary["status"] == "unproven"
    assert [row["status"] for row in summary["rows"]] == ["unproven", "unproven"]
    assert "unproven" in summary["rows"][0]["reason"]
    assert "unproven" in summary["rows"][1]["reason"]


def test_final_snapshot_without_apply_response_references_stays_unproven() -> None:
    summary = summarize_manifest_artifact_set_invariants(
        artifact_snapshots=[
            {
                "artifact_key": "correction_replay_examnet_pdf",
                "artifact_set_id": "crset-final",
                "content_sha256": "sha256:content-final",
                "observed_via": "final-download",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-final/"
                    "artifacts/correction_replay_examnet_pdf"
                    "?content_sha256=sha256%3Acontent-final"
                ),
                "product_route_observed": True,
                "request_digest": "sha256:final-request",
                "request_occurrence": 3,
                "status": 200,
            }
        ],
        correction_apply_requests=[
            {"body_sha256": "sha256:baseline-request", "request_id": "req-baseline"},
            {"body_sha256": "sha256:final-request", "request_id": "req-final"},
            {"body_sha256": "sha256:final-request", "request_id": "req-final-reload"},
        ],
        correction_apply_responses=[
            {"json": {"request_id": "req-baseline"}},
            {"json": {"request_id": "req-final"}},
            {"json": {"request_id": "req-final-reload"}},
        ],
    )

    assert summary["status"] == "unproven"
    assert [row["status"] for row in summary["rows"]] == ["unproven", "unproven"]


def test_product_route_snapshots_with_request_context_prove_duplicate_and_distinct_rows() -> None:
    summary = summarize_manifest_artifact_set_invariants(
        artifact_snapshots=[
            {
                "artifact_key": "correction_replay_examnet_pdf",
                "artifact_set_id": "crset-baseline",
                "content_sha256": "sha256:content-baseline",
                "observed_via": "exportable-baseline-download",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-baseline/"
                    "artifacts/correction_replay_examnet_pdf"
                    "?content_sha256=sha256%3Acontent-baseline"
                ),
                "product_route_observed": True,
                "request_digest": "sha256:baseline-request",
                "request_id": "req-baseline",
                "request_occurrence": 1,
                "status": 200,
            },
            {
                "artifact_key": "correction_replay_examnet_pdf",
                "artifact_set_id": "crset-final",
                "content_sha256": "sha256:content-final",
                "observed_via": "post-distinct-correction-download",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-final/"
                    "artifacts/correction_replay_examnet_pdf"
                    "?content_sha256=sha256%3Acontent-final"
                ),
                "product_route_observed": True,
                "request_digest": "sha256:final-request",
                "request_id": "req-final",
                "request_occurrence": 2,
                "status": 200,
            },
            {
                "artifact_key": "correction_replay_examnet_pdf",
                "artifact_set_id": "crset-final",
                "content_sha256": "sha256:content-final",
                "observed_via": "reload-final-download",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-final/"
                    "artifacts/correction_replay_examnet_pdf"
                    "?content_sha256=sha256%3Acontent-final"
                ),
                "product_route_observed": True,
                "request_digest": "sha256:final-request",
                "request_id": "req-final-reload",
                "request_occurrence": 3,
                "status": 200,
            },
        ],
        correction_apply_requests=[
            {"body_sha256": "sha256:baseline-request", "request_id": "req-baseline"},
            {"body_sha256": "sha256:final-request", "request_id": "req-final"},
            {"body_sha256": "sha256:final-request", "request_id": "req-final-reload"},
        ],
        correction_apply_responses=[
            {"json": {"request_id": "req-baseline"}},
            {"json": {"request_id": "req-final"}},
            {"json": {"request_id": "req-final-reload"}},
        ],
    )

    assert summary["status"] == "pass"
    assert summary["paired_observation_count"] == 3
    duplicate_row = summary["rows"][0]
    distinct_row = summary["rows"][1]
    assert duplicate_row["status"] == "pass"
    assert duplicate_row["request_digest"] == "sha256:final-request"
    assert duplicate_row["artifact_set_ids"] == ["crset-final"]
    assert distinct_row["status"] == "pass"
    assert distinct_row["request_digests"] == [
        "sha256:baseline-request",
        "sha256:final-request",
    ]
    assert distinct_row["artifact_set_ids"] == ["crset-baseline", "crset-final"]


def test_summary_retains_only_approved_public_metadata() -> None:
    summary = summarize_artifact_set_invariants(
        [
            {
                **_observation(
                    artifact_set_id="crset-final",
                    request_digest="sha256:final-v10",
                    request_occurrence=1,
                ),
                "headers": {"authorization": "must-not-retain"},
                "idempotency_key": "must-not-retain",
                "private_body_path": "/tmp/must-not-retain",
                "raw_body": "must-not-retain",
                "source_text": "must-not-retain",
            }
        ]
    )

    rendered = json.dumps(summary, ensure_ascii=False)
    assert "must-not-retain" not in rendered
    assert "raw_body" not in rendered
    assert "headers" not in rendered
    assert "private_body_path" not in rendered


def test_manifest_summary_pairs_apply_responses_only_when_product_route_observed() -> None:
    summary = summarize_manifest_artifact_set_invariants(
        artifact_snapshots=[
            {
                "content_sha256": "sha256:content-a",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-a/"
                    "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-a"
                ),
                "replay_artifact_key": "correction_replay_examnet_pdf",
                "replay_artifact_set_id": "crset-a",
                "status": 200,
                "ui_artifact_key": "examnet_pdf",
            },
            {
                "content_sha256": "sha256:content-b",
                "path": (
                    "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-b/"
                    "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-b"
                ),
                "replay_artifact_key": "correction_replay_examnet_pdf",
                "replay_artifact_set_id": "crset-b",
                "status": 200,
                "ui_artifact_key": "examnet_pdf",
            },
        ],
        correction_apply_requests=[
            {
                "body_sha256": "sha256:body-a",
                "corrections_sha256": "sha256:corrections-a",
                "request_id": "req-a",
            },
            {
                "body_sha256": "sha256:body-b",
                "corrections_sha256": "sha256:corrections-b",
                "request_id": "req-b",
            },
            {
                "body_sha256": "sha256:body-unobserved",
                "corrections_sha256": "sha256:corrections-unobserved",
                "request_id": "req-unobserved",
            },
        ],
        correction_apply_responses=[
            {
                "json": {
                    "request_id": "req-a",
                    "correction_replay_artifact_references": [
                        {
                            "artifact_key": "correction_replay_examnet_pdf",
                            "artifact_set_id": "crset-a",
                            "content_sha256": "sha256:content-a",
                            "request_id": "req-a",
                        }
                    ],
                }
            },
            {
                "json": {
                    "request_id": "req-b",
                    "correction_replay_artifact_references": [
                        {
                            "artifact_key": "correction_replay_examnet_pdf",
                            "artifact_set_id": "crset-b",
                            "content_sha256": "sha256:content-b",
                            "request_id": "req-b",
                        }
                    ],
                }
            },
            {
                "json": {
                    "request_id": "req-unobserved",
                    "correction_replay_artifact_references": [
                        {
                            "artifact_key": "correction_replay_examnet_pdf",
                            "artifact_set_id": "crset-unobserved",
                            "content_sha256": "sha256:content-unobserved",
                            "request_id": "req-unobserved",
                        }
                    ],
                }
            },
        ],
    )

    assert summary["status"] == "pass"
    assert summary["artifact_snapshot_count"] == 2
    assert summary["paired_observation_count"] == 2
    assert summary["rows"][1]["request_digests"] == ["sha256:body-a", "sha256:body-b"]
    assert summary["rows"][1]["artifact_set_ids"] == ["crset-a", "crset-b"]
    assert "crset-unobserved" not in json.dumps(summary, ensure_ascii=False)


def test_snapshot_recorder_refreshes_manifest_invariant_summary() -> None:
    summary: dict[str, object] = {
        "correction_apply_requests": [
            {
                "body_sha256": "sha256:body-a",
                "corrections_sha256": "sha256:corrections-a",
                "request_id": "req-a",
            },
            {
                "body_sha256": "sha256:body-b",
                "corrections_sha256": "sha256:corrections-b",
                "request_id": "req-b",
            },
        ],
        "correction_apply_responses": [
            {
                "json": {
                    "request_id": "req-a",
                    "correction_replay_artifact_references": [
                        {
                            "artifact_key": "correction_replay_examnet_pdf",
                            "artifact_set_id": "crset-a",
                            "content_sha256": "sha256:content-a",
                            "request_id": "req-a",
                        }
                    ],
                }
            },
            {
                "json": {
                    "request_id": "req-b",
                    "correction_replay_artifact_references": [
                        {
                            "artifact_key": "correction_replay_examnet_pdf",
                            "artifact_set_id": "crset-b",
                            "content_sha256": "sha256:content-b",
                            "request_id": "req-b",
                        }
                    ],
                }
            },
        ],
        "story58_artifact_set_snapshots": [],
    }

    record_story58_artifact_set_snapshot(
        summary,
        {
            "content_sha256": "sha256:content-a",
            "path": (
                "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-a/"
                "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-a"
            ),
            "replay_artifact_key": "correction_replay_examnet_pdf",
            "replay_artifact_set_id": "crset-a",
            "status": 200,
            "ui_artifact_key": "examnet_pdf",
        },
        observed_via="download",
    )
    record_story58_artifact_set_snapshot(
        summary,
        {
            "content_sha256": "sha256:content-b",
            "download_path": (
                "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-b/"
                "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-b"
            ),
            "download_status": 200,
            "replay_artifact_key": "correction_replay_examnet_pdf",
            "replay_artifact_set_id": "crset-b",
            "save_status": 200,
            "ui_artifact_key": "examnet_pdf",
        },
        observed_via="save",
    )

    invariant_summary = summary["story58_artifact_set_invariants"]
    assert _is_invariant_summary(invariant_summary)
    assert invariant_summary["status"] == "pass"
    assert invariant_summary["paired_observation_count"] == 2
    assert summary["story58_artifact_set_snapshots"] == [
        {
            "artifact_key": "correction_replay_examnet_pdf",
            "artifact_set_id": "crset-a",
            "content_sha256": "sha256:content-a",
            "observed_via": "download",
            "path": (
                "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-a/"
                "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-a"
            ),
            "product_route_observed": True,
            "status": 200,
            "ui_artifact_key": "examnet_pdf",
        },
        {
            "artifact_key": "correction_replay_examnet_pdf",
            "artifact_set_id": "crset-b",
            "content_sha256": "sha256:content-b",
            "observed_via": "save",
            "path": (
                "/sir-convert/v2/convert/jobs/job-1/correction-replays/crset-b/"
                "artifacts/correction_replay_examnet_pdf?content_sha256=sha256%3Acontent-b"
            ),
            "product_route_observed": True,
            "status": 200,
            "ui_artifact_key": "examnet_pdf",
        },
    ]
