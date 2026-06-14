"""Pure helpers for product-owned transcript formatter exports.

Domain purpose:
  Build Sir Convert replay requests, verify producer artifact authority, and
  project local Conversion Hub export rows into product-safe response state.

Relationships:
  - Used by `conversion_hub_transcript_formatter_exports`.
  - Reuses the replay parser for task-363 result and artifact manifest
    validation.
"""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportArtifact,
    ConversionHubTranscriptFormatterExportResponse,
    ConversionHubTranscriptFormatterExportStatus,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_MAX_BYTES,
    TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES,
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactRef,
    ConversionHubTranscriptFormatterReplayConversion,
    ConversionHubTranscriptFormatterReplayJobSpec,
    ConversionHubTranscriptFormatterReplayOptions,
    ConversionHubTranscriptFormatterReplayRetention,
    ConversionHubTranscriptFormatterReplaySource,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
    ConversionHubTranscriptSpeakerOverlayEntry,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay_parsing as replay_parsing,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_json_contract import (
    canonical_speaker_labels,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterProducerArtifact,
    ConversionHubTranscriptFormatterProducerRequest,
    ConversionHubTranscriptFormatterProducerResult,
)

USER_EXPORT_ERROR = "Exportfiler kunde inte skapas. Försök igen."


def build_replay_job_spec(
    *,
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
    overlays: list[ConversionHubTranscriptSpeakerOverlay],
) -> ConversionHubTranscriptFormatterReplayJobSpec:
    """Build the accepted task-363 replay JobSpec."""

    return ConversionHubTranscriptFormatterReplayJobSpec(
        source=ConversionHubTranscriptFormatterReplaySource(),
        conversion=ConversionHubTranscriptFormatterReplayConversion(),
        transcript_formatter_options=ConversionHubTranscriptFormatterReplayOptions(
            requested_artifacts=requested_artifacts,
            speaker_label_overrides=[
                ConversionHubTranscriptSpeakerOverlayEntry(
                    canonical_speaker_label=overlay.canonical_speaker_label,
                    display_name=overlay.display_name,
                )
                for overlay in overlays
            ],
        ),
        retention=ConversionHubTranscriptFormatterReplayRetention(),
    )


def build_producer_request(
    *,
    transcript: ConversionHubSavedTranscript,
    job_spec: ConversionHubTranscriptFormatterReplayJobSpec,
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
    correlation_id: str | None,
) -> ConversionHubTranscriptFormatterProducerRequest:
    """Build the server-owned multipart producer request."""

    return ConversionHubTranscriptFormatterProducerRequest(
        filename="saved-transcript.json",
        content_type="application/json",
        file_bytes=stable_json(transcript.transcript_json).encode("utf-8"),
        job_spec=job_spec.model_dump(mode="json"),
        requested_artifacts=tuple(requested_artifacts),
        idempotency_key=(
            f"idem_skriptoteket_transcript_export_"
            f"{export_digest(transcript=transcript, job_spec=job_spec)[:48]}"
        ),
        correlation_id=correlation_id,
        wait_seconds=0,
    )


def verify_successful_export(
    *,
    producer_result: ConversionHubTranscriptFormatterProducerResult,
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
) -> tuple[
    list[ConversionHubTranscriptFormatterArtifactRef],
    dict[ConversionHubTranscriptFormatterArtifactKey, bytes],
]:
    """Validate result, artifact manifest, and downloaded bytes before persistence."""

    if producer_result.sir_convert_job_id is None:
        raise malformed_producer_response("Sir Convert replay response is missing job id.")
    if producer_result.result is None or producer_result.artifact_manifest is None:
        raise malformed_producer_response("Sir Convert replay response is incomplete.")
    replay_parsing.parse_replay_result(
        payload=producer_result.result,
        sir_convert_job_id=producer_result.sir_convert_job_id,
    )
    artifact_refs = replay_parsing.parse_replay_artifact_refs(
        payload=producer_result.artifact_manifest,
        sir_convert_job_id=producer_result.sir_convert_job_id,
        requested_artifacts=requested_artifacts,
    )
    artifact_content = validated_producer_artifacts(
        artifact_refs=artifact_refs,
        producer_artifacts=producer_result.artifacts,
    )
    return artifact_refs, artifact_content


def validated_producer_artifacts(
    *,
    artifact_refs: list[ConversionHubTranscriptFormatterArtifactRef],
    producer_artifacts: dict[
        ConversionHubTranscriptFormatterArtifactKey,
        ConversionHubTranscriptFormatterProducerArtifact,
    ],
) -> dict[ConversionHubTranscriptFormatterArtifactKey, bytes]:
    """Verify downloaded producer bytes match the authoritative artifact refs."""

    expected_keys = {artifact.artifact_key for artifact in artifact_refs}
    if set(producer_artifacts) != expected_keys:
        raise malformed_producer_response("Sir Convert replay artifact downloads are incomplete.")
    total_bytes = 0
    artifact_content: dict[ConversionHubTranscriptFormatterArtifactKey, bytes] = {}
    for artifact_ref in artifact_refs:
        artifact = producer_artifacts[artifact_ref.artifact_key]
        if artifact.artifact_key != artifact_ref.artifact_key:
            raise malformed_producer_response("Sir Convert replay artifact key is invalid.")
        if content_type_base(artifact.content_type) != content_type_base(artifact_ref.content_type):
            raise malformed_producer_response(
                "Sir Convert replay artifact content type is invalid."
            )
        if len(artifact.content) != artifact_ref.size_bytes:
            raise malformed_producer_response("Sir Convert replay artifact size is invalid.")
        if len(artifact.content) > TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_MAX_BYTES:
            raise malformed_producer_response("Sir Convert replay artifact exceeds byte limit.")
        if hashlib.sha256(artifact.content).hexdigest() != plain_sha256(artifact_ref.sha256):
            raise malformed_producer_response("Sir Convert replay artifact checksum is invalid.")
        total_bytes += len(artifact.content)
        if total_bytes > TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES:
            raise malformed_producer_response("Sir Convert replay artifacts exceed byte limit.")
        artifact_content[artifact_ref.artifact_key] = artifact.content
    return artifact_content


def validate_overlay_inventory(
    *,
    transcript: ConversionHubSavedTranscript,
    overlays: list[ConversionHubTranscriptSpeakerOverlay],
) -> None:
    """Ensure speaker overlays reference canonical labels in the saved JSON."""

    canonical_labels = set(canonical_speaker_labels(transcript.transcript_json))
    for overlay in overlays:
        if overlay.canonical_speaker_label not in canonical_labels:
            raise validation_error("Speaker overlay labels must exist in the saved transcript.")


def validate_existing_export_job(
    *,
    job: ConversionHubJob,
    actor: User,
    transcript_id: UUID,
) -> None:
    """Ensure an idempotent upstream job belongs to this owner and transcript."""

    if job.owner_user_id != actor.id:
        raise not_found("ConversionHubJob", str(job.id))
    if (
        job.source_format is not ConversionHubSourceFormatV2.TRANSCRIPT_JSON
        or job.output_format is not ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE
        or job.input_filename != local_export_input_filename(transcript_id=transcript_id)
    ):
        raise validation_error("Replay job provenance does not match transcript exports.")


def response_from_job_and_records(
    *,
    transcript_id: UUID,
    job: ConversionHubJob,
    records: list[ConversionHubTranscriptFormatterArtifactRecord],
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat] | None = None,
) -> ConversionHubTranscriptFormatterExportResponse:
    """Project local job and artifact rows into the product export response."""

    response_requested_artifacts = (
        requested_artifacts
        if requested_artifacts is not None
        else [record.requested_artifact for record in records]
    )
    return ConversionHubTranscriptFormatterExportResponse(
        transcript_id=transcript_id,
        conversion_hub_job_id=job.id,
        status=product_status_from_job(job.status),
        requested_artifacts=response_requested_artifacts,
        artifacts=[
            ConversionHubTranscriptFormatterExportArtifact(
                requested_artifact=record.requested_artifact,
                artifact_key=record.artifact_key,
                filename=record.filename,
                content_type=record.content_type,
                size_bytes=record.size_bytes,
            )
            for record in records
        ],
        error_message=USER_EXPORT_ERROR if job.status is ConversionHubJobStatus.FAILED else None,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def product_status_from_job(
    status: ConversionHubJobStatus,
) -> ConversionHubTranscriptFormatterExportStatus:
    """Map local job ledger statuses to the product export state."""

    if status is ConversionHubJobStatus.SUCCEEDED:
        return ConversionHubTranscriptFormatterExportStatus.SUCCEEDED
    if status is ConversionHubJobStatus.FAILED or status is ConversionHubJobStatus.CANCELED:
        return ConversionHubTranscriptFormatterExportStatus.FAILED
    if status is ConversionHubJobStatus.PROCESSING:
        return ConversionHubTranscriptFormatterExportStatus.RUNNING
    return ConversionHubTranscriptFormatterExportStatus.PENDING


def job_status_from_producer(status: str) -> ConversionHubJobStatus:
    """Normalize producer statuses into the local job ledger enum."""

    normalized = status.strip().lower()
    if normalized == "running":
        normalized = "processing"
    return ConversionHubJobStatus.from_upstream(normalized)


def local_export_input_filename(*, transcript_id: UUID) -> str:
    """Return the product-local export job filename key for one transcript."""

    return f"saved-transcript-{transcript_id}.json"


def export_digest(
    *,
    transcript: ConversionHubSavedTranscript,
    job_spec: ConversionHubTranscriptFormatterReplayJobSpec,
) -> str:
    """Create a stable replay idempotency digest from transcript JSON and options."""

    digest_source = {
        "transcript_id": str(transcript.id),
        "transcript_json": transcript.transcript_json,
        "job_spec": job_spec.model_dump(mode="json"),
    }
    return hashlib.sha256(stable_json(digest_source).encode("utf-8")).hexdigest()


def stable_json(value: object) -> str:
    """Serialize JSON deterministically for producer bytes and idempotency."""

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def plain_sha256(value: str) -> str:
    """Normalize producer checksums with or without a `sha256:` prefix."""

    return value.removeprefix("sha256:").lower()


def content_type_base(value: str) -> str:
    """Compare media types without charset parameters."""

    return value.split(";", maxsplit=1)[0].strip().lower()


def safe_error_message(exc: DomainError) -> str:
    """Keep only local validation/not-found messages; hide upstream diagnostics."""

    if exc.code in {ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_FOUND}:
        return exc.message
    return USER_EXPORT_ERROR


def malformed_producer_response(message: str) -> DomainError:
    """Build a fail-closed producer drift error."""

    return DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=message,
        details={"upstream": "sir_convert_transcript_formatter_replay"},
    )
