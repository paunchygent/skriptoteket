"""Conversion Hub transcript formatter replay handlers.

Domain purpose:
  Prepare overlay-aware Sir Convert replay requests and record producer refs.

Relationships:
  - Uses saved transcript and speaker overlay repository protocols.
  - Records replay job provenance in the Conversion Hub job ledger.
  - Returns DTOs from `conversion_hub_transcript_replay` to the web boundary.
"""

from __future__ import annotations

import base64
import binascii
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
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_MAX_BYTES,
    TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES,
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactReceiptPayload,
    ConversionHubTranscriptFormatterArtifactRef,
    ConversionHubTranscriptFormatterReplayCompleteRequest,
    ConversionHubTranscriptFormatterReplayConversion,
    ConversionHubTranscriptFormatterReplayJobSpec,
    ConversionHubTranscriptFormatterReplayOptions,
    ConversionHubTranscriptFormatterReplayPrepareRequest,
    ConversionHubTranscriptFormatterReplayPrepareResponse,
    ConversionHubTranscriptFormatterReplayResponse,
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
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.conversion_hub import (
    ConversionHubJobRepositoryProtocol,
    ConversionHubSavedTranscriptRepositoryProtocol,
    ConversionHubTranscriptFormatterArtifactReceiptVerifierProtocol,
    ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
    ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_REPLAY_CONTENT_TYPE = "application/json"
_IDEMPOTENCY_PREFIX = "idem_skriptoteket_transcript_replay_"
_CORRELATION_PREFIX = "corr_skriptoteket_transcript_replay_"
_REQUESTED_ARTIFACT_BY_KEY = {
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: (
        ConversionHubTranscriptFormatterArtifactFormat.TXT
    ),
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: (
        ConversionHubTranscriptFormatterArtifactFormat.MD
    ),
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT: (
        ConversionHubTranscriptFormatterArtifactFormat.VTT
    ),
    ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT: (
        ConversionHubTranscriptFormatterArtifactFormat.SRT
    ),
}


class PrepareConversionHubTranscriptFormatterReplayHandler:
    """Prepare a strict replay request from saved transcript and speaker overlays."""

    def __init__(
        self,
        *,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        speaker_overlays: ConversionHubTranscriptSpeakerOverlayRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._transcripts = transcripts
        self._speaker_overlays = speaker_overlays
        self._uow = uow
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        transcript_id: UUID,
        request: ConversionHubTranscriptFormatterReplayPrepareRequest,
        correlation_id: str | None,
    ) -> ConversionHubTranscriptFormatterReplayPrepareResponse:
        async with self._uow:
            transcript = await self._load_transcript(actor=actor, transcript_id=transcript_id)
            overlays = await self._speaker_overlays.list_for_transcript(
                owner_user_id=actor.id,
                transcript_id=transcript.id,
            )
        if not overlays:
            raise validation_error("Save speaker names before requesting transcript export.")
        _validate_overlay_inventory(transcript=transcript, overlays=overlays)
        gateway_filename = _gateway_filename(transcript_id=transcript.id)
        job_spec = _build_replay_job_spec(
            gateway_filename=gateway_filename,
            requested_artifacts=request.requested_artifacts,
            overlays=overlays,
        )
        digest = _replay_digest(transcript=transcript, job_spec=job_spec)
        return ConversionHubTranscriptFormatterReplayPrepareResponse(
            transcript_id=transcript.id,
            correlation_id=correlation_id
            or f"{_CORRELATION_PREFIX}{self._id_generator.new_uuid()}",
            idempotency_key=f"{_IDEMPOTENCY_PREFIX}{digest[:48]}",
            gateway_filename=gateway_filename,
            content_type=_REPLAY_CONTENT_TYPE,
            transcript_json=transcript.transcript_json,
            job_spec=job_spec,
        )

    async def _load_transcript(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript:
        transcript = await self._transcripts.get_by_owner_and_id(
            owner_user_id=actor.id,
            transcript_id=transcript_id,
        )
        if transcript is None:
            raise not_found("ConversionHubSavedTranscript", str(transcript_id))
        return transcript


class CompleteConversionHubTranscriptFormatterReplayHandler:
    """Record a completed replay job and return accepted artifact refs."""

    def __init__(
        self,
        *,
        jobs: ConversionHubJobRepositoryProtocol,
        transcripts: ConversionHubSavedTranscriptRepositoryProtocol,
        artifacts: ConversionHubTranscriptFormatterArtifactRepositoryProtocol,
        receipt_verifier: ConversionHubTranscriptFormatterArtifactReceiptVerifierProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._jobs = jobs
        self._transcripts = transcripts
        self._artifacts = artifacts
        self._receipt_verifier = receipt_verifier
        self._uow = uow
        self._clock = clock
        self._id_generator = id_generator

    async def handle(
        self,
        *,
        actor: User,
        authenticated_huleedu_subject: str,
        transcript_id: UUID,
        request: ConversionHubTranscriptFormatterReplayCompleteRequest,
    ) -> ConversionHubTranscriptFormatterReplayResponse:
        replay_parsing.parse_replay_result(
            payload=request.result,
            sir_convert_job_id=request.sir_convert_job_id,
        )
        verified_receipts = _verified_artifact_receipts(
            request=request,
            receipt_verifier=self._receipt_verifier,
            authenticated_huleedu_subject=authenticated_huleedu_subject,
            now_ts=int(self._clock.now().timestamp()),
        )
        artifact_refs = _artifact_refs_from_receipts(
            receipts=verified_receipts,
            request=request,
        )
        artifact_payloads = _validated_artifact_payloads(
            artifact_refs=artifact_refs,
            request=request,
        )
        async with self._uow:
            transcript = await self._load_transcript(actor=actor, transcript_id=transcript_id)
            job = await self._create_or_reuse_job(
                actor=actor,
                transcript=transcript,
                request=request,
            )
            await self._artifacts.replace_for_replay(
                records=[
                    ConversionHubTranscriptFormatterArtifactRecord(
                        id=self._id_generator.new_uuid(),
                        owner_user_id=actor.id,
                        transcript_id=transcript.id,
                        conversion_hub_job_id=job.id,
                        sir_convert_job_id=request.sir_convert_job_id,
                        requested_artifact=artifact.requested_artifact,
                        artifact_key=artifact.artifact_key,
                        filename=artifact.filename,
                        content_type=artifact.content_type,
                        size_bytes=artifact.size_bytes,
                        sha256=artifact.sha256,
                        retrieval_path=artifact.retrieval_path,
                        content=artifact_payloads[artifact.artifact_key],
                        created_at=self._clock.now(),
                        updated_at=self._clock.now(),
                    )
                    for artifact in artifact_refs
                ],
            )
        return ConversionHubTranscriptFormatterReplayResponse(
            transcript_id=transcript.id,
            conversion_hub_job_id=job.id,
            sir_convert_job_id=request.sir_convert_job_id,
            correlation_id=request.correlation_id,
            requested_artifacts=request.requested_artifacts,
            artifacts=artifact_refs,
        )

    async def _load_transcript(
        self,
        *,
        actor: User,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript:
        transcript = await self._transcripts.get_by_owner_and_id(
            owner_user_id=actor.id,
            transcript_id=transcript_id,
        )
        if transcript is None:
            raise not_found("ConversionHubSavedTranscript", str(transcript_id))
        return transcript

    async def _create_or_reuse_job(
        self,
        *,
        actor: User,
        transcript: ConversionHubSavedTranscript,
        request: ConversionHubTranscriptFormatterReplayCompleteRequest,
    ) -> ConversionHubJob:
        existing = await self._jobs.get_by_upstream_job_id(
            upstream_job_id=request.sir_convert_job_id
        )
        if existing is not None:
            if existing.owner_user_id != actor.id:
                raise not_found("ConversionHubJob", request.sir_convert_job_id)
            _validate_existing_replay_job(
                existing,
                expected_input_filename=_gateway_filename(transcript_id=transcript.id),
            )
            return existing
        now = self._clock.now()
        return await self._jobs.create(
            job=ConversionHubJob(
                id=self._id_generator.new_uuid(),
                owner_user_id=actor.id,
                input_filename=_gateway_filename(transcript_id=transcript.id),
                source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
                output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
                pdf_layout=None,
                upstream_job_id=request.sir_convert_job_id,
                status=ConversionHubJobStatus.SUCCEEDED,
                correlation_id=request.correlation_id,
                error_message=None,
                created_at=now,
                updated_at=now,
            )
        )


def _validate_existing_replay_job(
    job: ConversionHubJob,
    *,
    expected_input_filename: str,
) -> None:
    if (
        job.source_format is not ConversionHubSourceFormatV2.TRANSCRIPT_JSON
        or job.output_format is not ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE
        or job.status is not ConversionHubJobStatus.SUCCEEDED
        or job.input_filename != expected_input_filename
    ):
        raise validation_error("Replay job provenance does not match transcript exports.")


def _validated_artifact_payloads(
    *,
    artifact_refs: list[ConversionHubTranscriptFormatterArtifactRef],
    request: ConversionHubTranscriptFormatterReplayCompleteRequest,
) -> dict[ConversionHubTranscriptFormatterArtifactKey, bytes]:
    refs_by_key = {artifact.artifact_key: artifact for artifact in artifact_refs}
    payloads: dict[ConversionHubTranscriptFormatterArtifactKey, bytes] = {}
    total_bytes = 0
    for payload in request.artifact_payloads:
        if payload.artifact_key in payloads:
            raise validation_error("Replay artifact payload keys are duplicated.")
        ref = refs_by_key.get(payload.artifact_key)
        if ref is None:
            raise validation_error("Replay artifact payload is not in the producer manifest.")
        content = _decode_artifact_payload(payload.content_base64)
        if _content_type_base(payload.content_type) != _content_type_base(ref.content_type):
            raise validation_error("Replay artifact payload content type is invalid.")
        _validate_artifact_payload_content(ref=ref, content=content)
        total_bytes += len(content)
        if total_bytes > TRANSCRIPT_FORMATTER_REPLAY_TOTAL_ARTIFACT_MAX_BYTES:
            raise validation_error("Replay artifact payloads exceed the total byte limit.")
        payloads[payload.artifact_key] = content
    missing = [
        artifact.artifact_key for artifact in artifact_refs if artifact.artifact_key not in payloads
    ]
    if missing:
        raise validation_error("Replay artifact payloads are incomplete.")
    return payloads


def _verified_artifact_receipts(
    *,
    request: ConversionHubTranscriptFormatterReplayCompleteRequest,
    receipt_verifier: ConversionHubTranscriptFormatterArtifactReceiptVerifierProtocol,
    authenticated_huleedu_subject: str,
    now_ts: int,
) -> dict[
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterArtifactReceiptPayload,
]:
    receipts: dict[
        ConversionHubTranscriptFormatterArtifactKey,
        ConversionHubTranscriptFormatterArtifactReceiptPayload,
    ] = {}
    for payload in request.artifact_payloads:
        if payload.artifact_key in receipts:
            raise validation_error("Replay artifact payload keys are duplicated.")
        receipt = receipt_verifier.verify(receipt=payload.receipt, now_ts=now_ts)
        if receipt.sub != authenticated_huleedu_subject:
            raise validation_error("Replay artifact receipt subject does not match actor.")
        if receipt.artifact_key != payload.artifact_key:
            raise validation_error("Replay artifact receipt key does not match payload.")
        if receipt.sir_convert_job_id != request.sir_convert_job_id:
            raise validation_error("Replay artifact receipt job does not match replay.")
        receipts[payload.artifact_key] = receipt
    return receipts


def _artifact_refs_from_receipts(
    *,
    receipts: dict[
        ConversionHubTranscriptFormatterArtifactKey,
        ConversionHubTranscriptFormatterArtifactReceiptPayload,
    ],
    request: ConversionHubTranscriptFormatterReplayCompleteRequest,
) -> list[ConversionHubTranscriptFormatterArtifactRef]:
    requested_keys = {
        _artifact_key_for_requested_artifact(requested_artifact)
        for requested_artifact in request.requested_artifacts
    }
    receipt_keys = set(receipts)
    if receipt_keys != requested_keys:
        raise validation_error("Replay artifact receipts do not match requested artifacts.")
    artifact_refs: list[ConversionHubTranscriptFormatterArtifactRef] = []
    for requested_artifact in request.requested_artifacts:
        artifact_key = _artifact_key_for_requested_artifact(requested_artifact)
        receipt = receipts[artifact_key]
        artifact_refs.append(
            ConversionHubTranscriptFormatterArtifactRef(
                requested_artifact=requested_artifact,
                artifact_key=artifact_key,
                filename=receipt.filename,
                content_type=receipt.content_type,
                size_bytes=receipt.size_bytes,
                sha256=receipt.sha256,
                retrieval_path=receipt.retrieval_path,
            )
        )
    return artifact_refs


def _artifact_key_for_requested_artifact(
    requested_artifact: ConversionHubTranscriptFormatterArtifactFormat,
) -> ConversionHubTranscriptFormatterArtifactKey:
    for artifact_key, artifact_format in _REQUESTED_ARTIFACT_BY_KEY.items():
        if artifact_format == requested_artifact:
            return artifact_key
    raise validation_error("Requested replay artifact is unsupported.")


def _decode_artifact_payload(content_base64: str) -> bytes:
    try:
        return base64.b64decode(content_base64, validate=True)
    except binascii.Error as exc:
        raise validation_error("Replay artifact payload is not valid base64.") from exc


def _validate_artifact_payload_content(
    *,
    ref: ConversionHubTranscriptFormatterArtifactRef,
    content: bytes,
) -> None:
    if len(content) != ref.size_bytes:
        raise validation_error("Replay artifact payload size is invalid.")
    if len(content) > TRANSCRIPT_FORMATTER_REPLAY_ARTIFACT_MAX_BYTES:
        raise validation_error("Replay artifact payload exceeds the per-artifact byte limit.")
    if hashlib.sha256(content).hexdigest() != _plain_sha256(ref.sha256):
        raise validation_error("Replay artifact payload checksum is invalid.")


def _plain_sha256(value: str) -> str:
    return value.removeprefix("sha256:").lower()


def _content_type_base(value: str) -> str:
    return value.split(";", maxsplit=1)[0].strip().lower()


def _build_replay_job_spec(
    *,
    gateway_filename: str,
    requested_artifacts: list[ConversionHubTranscriptFormatterArtifactFormat],
    overlays: list[ConversionHubTranscriptSpeakerOverlay],
) -> ConversionHubTranscriptFormatterReplayJobSpec:
    return ConversionHubTranscriptFormatterReplayJobSpec(
        source=ConversionHubTranscriptFormatterReplaySource(filename=gateway_filename),
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


def _validate_overlay_inventory(
    *,
    transcript: ConversionHubSavedTranscript,
    overlays: list[ConversionHubTranscriptSpeakerOverlay],
) -> None:
    canonical_labels = set(canonical_speaker_labels(transcript.transcript_json))
    for overlay in overlays:
        if overlay.canonical_speaker_label not in canonical_labels:
            raise validation_error("Speaker overlay labels must exist in the saved transcript.")


def _gateway_filename(*, transcript_id: UUID) -> str:
    return f"saved-transcript-{transcript_id}.json"


def _replay_digest(
    *,
    transcript: ConversionHubSavedTranscript,
    job_spec: ConversionHubTranscriptFormatterReplayJobSpec,
) -> str:
    digest_source = {
        "transcript_id": str(transcript.id),
        "transcript_json": transcript.transcript_json,
        "job_spec": job_spec.model_dump(mode="json"),
    }
    return hashlib.sha256(_stable_json(digest_source).encode("utf-8")).hexdigest()


def _stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
