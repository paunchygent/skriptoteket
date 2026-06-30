"""Story 58 artifact observation assembly.

Domain purpose:
    Normalize retained product-route artifact snapshots into safe observation
    rows that can be compared against correction request digests for Story 58
    proof invariants.

Relationships:
    - Used by `scripts._story58_artifact_set_invariants` to keep invariant
      classification separate from manifest-shape extraction.
    - Consumes only public artifact/request digest metadata emitted by the
      PR-0337 proof harness.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def observed_artifacts_from_snapshots(
    artifact_snapshots: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Return route-observed artifact authority rows from retained snapshots."""

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
                "corrections_sha256": _first_string(snapshot, ("corrections_sha256",)),
                "job_id": _first_string(snapshot, ("job_id",)),
                "path": _first_string(snapshot, ("path", "download_path")),
                "request_digest": _first_string(snapshot, ("request_digest",)),
                "request_id": _first_string(snapshot, ("request_id",)),
                "request_occurrence": _first_int(snapshot, ("request_occurrence",)),
                "source_bundle_id": _first_string(snapshot, ("source_bundle_id",)),
                "source_file_sha256": _first_string(snapshot, ("source_file_sha256",)),
                "source_state_sha256": _first_string(snapshot, ("source_state_sha256",)),
                "status": _first_int(snapshot, ("status", "save_status")),
                "ui_artifact_key": _first_string(snapshot, ("ui_artifact_key",)),
            }
        )
    return artifacts


def snapshot_manifest_observations(
    observed_artifacts: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Return digest-bound observations from product-route artifact snapshots."""

    observations: list[dict[str, object]] = []
    for artifact in observed_artifacts:
        request_digest = artifact.get("request_digest")
        if not isinstance(request_digest, str) or not request_digest:
            continue
        observation = {
            "artifact_key": artifact["artifact_key"],
            "artifact_set_id": artifact["artifact_set_id"],
            "content_sha256": artifact["content_sha256"],
            "product_route_observed": True,
            "request_digest": request_digest,
        }
        _copy_optional_keys(
            observation,
            artifact,
            (
                "corrections_sha256",
                "job_id",
                "path",
                "request_id",
                "request_occurrence",
                "source_bundle_id",
                "source_file_sha256",
                "source_state_sha256",
                "status",
                "ui_artifact_key",
            ),
        )
        observations.append(observation)
    return observations


def deduped_observations(
    observations: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Remove duplicate observation rows without collapsing replay occurrences."""

    deduped: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for observation in observations:
        key = (
            observation.get("artifact_set_id"),
            observation.get("artifact_key"),
            observation.get("content_sha256"),
            observation.get("request_digest"),
            observation.get("request_occurrence"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(observation))
    return deduped


def _copy_optional_keys(
    target: dict[str, object],
    source: Mapping[str, object],
    keys: tuple[str, ...],
) -> None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value:
            target[key] = value
        elif isinstance(value, int):
            target[key] = value


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
