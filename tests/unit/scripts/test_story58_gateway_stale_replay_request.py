"""Story 58 Gateway stale-replay request-contract tests.

Domain purpose:
    Prove deterministic request construction and fingerprinting for the
    authenticated Story 58 Gateway replay proof.

Relationships:
    Exercises `scripts._story58_gateway_stale_replay_request`, which feeds
    `scripts.story58_gateway_stale_replay_proof`.
"""

from __future__ import annotations

from scripts._story58_gateway_stale_replay_request import (
    build_story58_gateway_job_spec,
    stable_story58_gateway_json,
    story58_request_fingerprint,
    story58_scope_digest,
    story58_sha256_bytes,
)


def test_story58_gateway_job_spec_and_fingerprints_are_stable() -> None:
    job_spec = build_story58_gateway_job_spec("ak7_lag_och_ratt_with_image.dxe")
    job_spec_json = stable_story58_gateway_json(job_spec)
    file_sha256 = story58_sha256_bytes(b"fixture-dxe-bytes")

    assert job_spec["source"] == {
        "kind": "upload",
        "filename": "ak7_lag_och_ratt_with_image.dxe",
        "format": "digiexam_dxe",
    }
    assert story58_request_fingerprint(
        job_spec_json=job_spec_json,
        file_sha256=file_sha256,
    ) == story58_sha256_bytes(f"{job_spec_json}:{file_sha256}:::::".encode("utf-8"))
    assert story58_scope_digest(
        owner_scope="identity:v1:user:sha256:owner",
        idempotency_key="proof-idempotency",
    ) == story58_sha256_bytes(
        b"identity:v1:user:sha256:owner:POST:/v2/convert/jobs:proof-idempotency"
    )
