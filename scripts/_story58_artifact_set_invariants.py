"""Story 58 correction replay artifact-set invariant support.

Domain purpose:
    Classify public Story 58 correction apply proof observations by comparing
    safe correction request digests with replay artifact-set ids observed
    through product-route artifact downloads.

Relationships:
    - Used by `scripts.playwright_pr_0337_correction_session_live` to attach a
      fail-closed invariant summary to retained proof manifests.
    - Complements private request capture by consuming only public digest and
      artifact metadata, never raw correction bodies or uploaded/source text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

APPROVED_OBSERVATION_KEYS = (
    "artifact_key",
    "artifact_set_id",
    "content_sha256",
    "corrections_sha256",
    "job_id",
    "observed_via",
    "path",
    "product_route_observed",
    "request_digest",
    "request_id",
    "request_occurrence",
    "source_bundle_id",
    "source_file_sha256",
    "source_state_sha256",
    "status",
    "ui_artifact_key",
)
SUMMARY_SCHEMA_VERSION = "story58_artifact_set_invariant_summary_v1"


def summarize_artifact_set_invariants(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Return a redacted duplicate/distinct artifact-set invariant summary.

    Args:
        observations: Safe request digest and artifact-set observations. The
            helper only trusts observations whose product route was observed.

    Returns:
        Public invariant summary with `pass`, `fail`, or `unproven` rows.
    """

    safe_observations = [_safe_observation(row) for row in observations]
    route_observations = [
        row
        for row in safe_observations
        if row.get("product_route_observed") is True
        and _non_empty_string(row.get("request_digest"))
        and _non_empty_string(row.get("artifact_set_id"))
        and _non_empty_string(row.get("content_sha256"))
    ]
    rows = [
        _duplicate_request_digest_row(route_observations),
        _distinct_request_digest_row(route_observations),
    ]
    return {
        "approved_metadata_only": True,
        "observation_count": len(safe_observations),
        "product_route_observation_count": len(route_observations),
        "rows": rows,
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "status": _summary_status(rows),
    }


def summarize_manifest_artifact_set_invariants(
    *,
    artifact_snapshots: Sequence[Mapping[str, object]],
    correction_apply_requests: Sequence[Mapping[str, object]],
    correction_apply_responses: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Summarize Story 58 invariants from public proof-manifest metadata.

    Args:
        artifact_snapshots: Product-route artifact download/save metadata.
        correction_apply_requests: Redacted correction apply request summaries.
        correction_apply_responses: Redacted correction apply response summaries.

    Returns:
        Public invariant summary derived only from approved metadata.
    """

    observations = _manifest_observations(
        artifact_snapshots=artifact_snapshots,
        correction_apply_requests=correction_apply_requests,
        correction_apply_responses=correction_apply_responses,
    )
    summary = summarize_artifact_set_invariants(observations)
    summary["artifact_snapshot_count"] = len(artifact_snapshots)
    summary["paired_observation_count"] = len(observations)
    return summary


def record_story58_artifact_set_snapshot(
    summary: dict[str, object],
    evidence: Mapping[str, object],
    *,
    observed_via: str,
) -> None:
    """Attach one product-route artifact snapshot and refresh invariants."""

    snapshot = story58_artifact_set_snapshot(evidence, observed_via=observed_via)
    snapshots = summary.setdefault("story58_artifact_set_snapshots", [])
    if not isinstance(snapshots, list):
        raise AssertionError("Story 58 artifact snapshots must be a list.")
    snapshots.append(snapshot)
    refresh_story58_artifact_set_invariants(summary)


def refresh_story58_artifact_set_invariants(summary: dict[str, object]) -> None:
    """Refresh the public invariant summary on an in-flight proof manifest."""

    summary["story58_artifact_set_invariants"] = summarize_manifest_artifact_set_invariants(
        artifact_snapshots=_mapping_rows(summary.get("story58_artifact_set_snapshots")),
        correction_apply_requests=_mapping_rows(summary.get("correction_apply_requests")),
        correction_apply_responses=_mapping_rows(summary.get("correction_apply_responses")),
    )


def story58_artifact_set_snapshot(
    evidence: Mapping[str, object],
    *,
    observed_via: str,
) -> dict[str, object]:
    """Return approved metadata from one product-route replay artifact response."""

    artifact_set_id = evidence.get("replay_artifact_set_id") or evidence.get("artifact_set_id")
    artifact_key = evidence.get("replay_artifact_key") or evidence.get("artifact_key")
    content_sha256 = evidence.get("content_sha256")
    path = evidence.get("path") or evidence.get("download_path")
    status = (
        evidence.get("status") or evidence.get("download_status") or evidence.get("save_status")
    )
    if not (
        isinstance(artifact_set_id, str)
        and artifact_set_id
        and isinstance(artifact_key, str)
        and artifact_key
        and isinstance(content_sha256, str)
        and content_sha256
    ):
        raise AssertionError("Story 58 artifact snapshot is missing replay artifact authority.")
    snapshot: dict[str, object] = {
        "artifact_key": artifact_key,
        "artifact_set_id": artifact_set_id,
        "content_sha256": content_sha256,
        "observed_via": observed_via,
        "product_route_observed": True,
    }
    if isinstance(path, str) and path:
        snapshot["path"] = path
    if isinstance(status, int):
        snapshot["status"] = status
    ui_artifact_key = evidence.get("ui_artifact_key")
    if isinstance(ui_artifact_key, str) and ui_artifact_key:
        snapshot["ui_artifact_key"] = ui_artifact_key
    return snapshot


def _safe_observation(observation: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key in APPROVED_OBSERVATION_KEYS:
        value = observation.get(key)
        if isinstance(value, str) and value:
            safe[key] = value
        elif isinstance(value, bool):
            safe[key] = value
        elif isinstance(value, int):
            safe[key] = value
    return safe


def _mapping_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _manifest_observations(
    *,
    artifact_snapshots: Sequence[Mapping[str, object]],
    correction_apply_requests: Sequence[Mapping[str, object]],
    correction_apply_responses: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    observed_artifacts = _observed_artifacts(artifact_snapshots)
    requests_by_id = _requests_by_id(correction_apply_requests)
    observations: list[dict[str, object]] = []
    for index, response in enumerate(correction_apply_responses, start=1):
        response_json = response.get("json")
        if not isinstance(response_json, dict):
            continue
        request_id = response_json.get("request_id")
        request = requests_by_id.get(request_id) if isinstance(request_id, str) else None
        if request is None and index <= len(correction_apply_requests):
            request = correction_apply_requests[index - 1]
        references = response_json.get("correction_replay_artifact_references")
        if not isinstance(references, list):
            continue
        for reference in references:
            if not isinstance(reference, dict):
                continue
            artifact = _matching_observed_artifact(reference, observed_artifacts)
            if artifact is None:
                continue
            observations.append(
                _manifest_observation(
                    artifact=artifact,
                    reference=reference,
                    request=request,
                    request_occurrence=index,
                )
            )
    return observations


def _observed_artifacts(
    artifact_snapshots: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    artifacts: list[dict[str, object]] = []
    for snapshot in artifact_snapshots:
        artifact_set_id = _first_string(snapshot, ("artifact_set_id", "replay_artifact_set_id"))
        artifact_key = _first_string(snapshot, ("artifact_key", "replay_artifact_key"))
        content_sha256 = _first_string(snapshot, ("content_sha256",))
        if not artifact_set_id or not artifact_key or not content_sha256:
            continue
        artifacts.append(
            {
                "artifact_key": artifact_key,
                "artifact_set_id": artifact_set_id,
                "content_sha256": content_sha256,
                "path": _first_string(snapshot, ("path", "download_path")),
                "status": _first_int(snapshot, ("status", "save_status")),
                "ui_artifact_key": _first_string(snapshot, ("ui_artifact_key",)),
            }
        )
    return artifacts


def _requests_by_id(
    correction_apply_requests: Sequence[Mapping[str, object]],
) -> dict[object, Mapping[str, object]]:
    return {
        request["request_id"]: request
        for request in correction_apply_requests
        if isinstance(request.get("request_id"), str) and request.get("request_id")
    }


def _matching_observed_artifact(
    reference: Mapping[str, object],
    observed_artifacts: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    reference_artifact_set_id = reference.get("artifact_set_id")
    reference_artifact_key = reference.get("artifact_key")
    reference_content_sha256 = reference.get("content_sha256")
    for artifact in observed_artifacts:
        if (
            artifact.get("artifact_set_id") == reference_artifact_set_id
            and artifact.get("artifact_key") == reference_artifact_key
            and artifact.get("content_sha256") == reference_content_sha256
        ):
            return artifact
    return None


def _manifest_observation(
    *,
    artifact: Mapping[str, object],
    reference: Mapping[str, object],
    request: Mapping[str, object] | None,
    request_occurrence: int,
) -> dict[str, object]:
    request_digest = (
        _first_string(request or {}, ("body_sha256", "request_digest", "corrections_sha256"))
        or _first_string(reference, ("correction_payload_digest",))
        or ""
    )
    observation: dict[str, object] = {
        "artifact_key": artifact["artifact_key"],
        "artifact_set_id": artifact["artifact_set_id"],
        "content_sha256": artifact["content_sha256"],
        "product_route_observed": True,
        "request_digest": request_digest,
        "request_occurrence": request_occurrence,
    }
    _copy_optional(observation, artifact, "path")
    _copy_optional(observation, artifact, "status")
    _copy_optional(observation, artifact, "ui_artifact_key")
    _copy_optional(observation, reference, "request_id")
    _copy_optional(observation, reference, "source_binding_digest")
    _copy_optional(observation, reference, "source_state_sha256")
    _copy_optional(observation, reference, "correction_payload_digest", to_key="corrections_sha256")
    if request is not None:
        _copy_optional(observation, request, "request_id")
        _copy_optional(observation, request, "corrections_sha256")
        _copy_optional(observation, request, "source_bundle_id")
        _copy_optional(observation, request, "source_file_sha256")
        _copy_optional(observation, request, "source_state_sha256")
    return observation


def _duplicate_request_digest_row(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    groups = _groups_by_request_digest(observations)
    duplicate_groups = [
        _request_digest_group_summary(request_digest, rows)
        for request_digest, rows in groups.items()
        if len(_request_occurrences(rows)) >= 2
    ]
    if not duplicate_groups:
        return {
            "invariant": "duplicate_request_digest_same_artifact_set",
            "reason": "unproven: fewer than two product-route observations share a request digest",
            "status": "unproven",
        }

    failing_groups = [group for group in duplicate_groups if len(group["artifact_set_ids"]) != 1]
    selected_group = failing_groups[0] if failing_groups else duplicate_groups[0]
    row = {
        "artifact_set_ids": selected_group["artifact_set_ids"],
        "invariant": "duplicate_request_digest_same_artifact_set",
        "request_digest": selected_group["request_digest"],
        "request_ids": selected_group["request_ids"],
        "request_occurrence_count": selected_group["request_occurrence_count"],
        "status": "fail" if failing_groups else "pass",
    }
    if len(duplicate_groups) > 1:
        row["groups"] = duplicate_groups
    return row


def _distinct_request_digest_row(observations: Sequence[Mapping[str, object]]) -> dict[str, object]:
    groups = _groups_by_request_digest(observations)
    digest_groups = [
        _request_digest_group_summary(request_digest, rows)
        for request_digest, rows in groups.items()
    ]
    if len(digest_groups) < 2:
        return {
            "invariant": "distinct_request_digests_distinct_artifact_sets",
            "reason": "unproven: fewer than two request digests have product-route observations",
            "status": "unproven",
        }

    artifact_set_ids = _unique_sorted(
        artifact_set_id for group in digest_groups for artifact_set_id in group["artifact_set_ids"]
    )
    request_digests = _unique_sorted(group["request_digest"] for group in digest_groups)
    status = "pass" if len(artifact_set_ids) == len(request_digests) else "fail"
    return {
        "artifact_set_ids": artifact_set_ids,
        "invariant": "distinct_request_digests_distinct_artifact_sets",
        "request_digests": request_digests,
        "request_occurrence_count": sum(
            int(group["request_occurrence_count"]) for group in digest_groups
        ),
        "status": status,
    }


def _groups_by_request_digest(
    observations: Sequence[Mapping[str, object]],
) -> dict[str, list[Mapping[str, object]]]:
    groups: dict[str, list[Mapping[str, object]]] = {}
    for observation in observations:
        request_digest = observation.get("request_digest")
        if not isinstance(request_digest, str) or not request_digest:
            continue
        groups.setdefault(request_digest, []).append(observation)
    return groups


def _request_digest_group_summary(
    request_digest: str,
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "artifact_set_ids": _unique_sorted(row.get("artifact_set_id") for row in rows),
        "request_digest": request_digest,
        "request_ids": _unique_sorted(row.get("request_id") for row in rows),
        "request_occurrence_count": len(_request_occurrences(rows)),
    }


def _request_occurrences(rows: Sequence[Mapping[str, object]]) -> set[str]:
    occurrences: set[str] = set()
    for index, row in enumerate(rows):
        occurrence = row.get("request_occurrence")
        if isinstance(occurrence, int):
            occurrences.add(str(occurrence))
            continue
        if isinstance(occurrence, str) and occurrence:
            occurrences.add(occurrence)
            continue
        request_id = row.get("request_id")
        occurrences.add(
            str(request_id) if isinstance(request_id, str) and request_id else str(index)
        )
    return occurrences


def _unique_sorted(values: Iterable[object]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _summary_status(rows: Sequence[Mapping[str, object]]) -> str:
    statuses = [row.get("status") for row in rows]
    if "fail" in statuses:
        return "fail"
    if "pass" in statuses:
        return "pass"
    return "unproven"


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _first_string(payload: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _first_int(payload: Mapping[str, object], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return None


def _copy_optional(
    target: dict[str, object],
    source: Mapping[str, object],
    key: str,
    *,
    to_key: str | None = None,
) -> None:
    value = source.get(key)
    if isinstance(value, str) and value:
        target[to_key or key] = value
    elif isinstance(value, int):
        target[to_key or key] = value
