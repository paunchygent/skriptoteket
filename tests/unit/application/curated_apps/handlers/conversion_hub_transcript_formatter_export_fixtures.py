"""Fixtures for product-owned transcript formatter export tests.

Domain purpose:
  Provide in-memory Conversion Hub export repositories and producer fixtures so
  handler specs can focus on product export behavior instead of setup plumbing.

Relationships:
  - Used by `test_conversion_hub_transcript_formatter_exports`.
  - Mirrors repository and producer protocol boundaries without database or
    network IO.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportStateRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_exports as export_handlers,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.protocols.conversion_hub import (
    ConversionHubTranscriptFormatterProducerArtifact,
    ConversionHubTranscriptFormatterProducerProtocol,
    ConversionHubTranscriptFormatterProducerRequest,
    ConversionHubTranscriptFormatterProducerResult,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptSpeakerOverlayRepository,
    SequentialIdGenerator,
)

NOW = datetime(2026, 6, 14, 10, 0, tzinfo=timezone.utc)
TXT = "Anna: Hej.\nBo: Valkommen.\n".encode("utf-8")
MD = "## Transkript\n\nAnna: Hej.\n\nBo: Valkommen.\n".encode("utf-8")
VTT = b"WEBVTT\n\n00:00.000 --> 00:02.000\nAnna: Hej.\n"
SRT = b"1\n00:00:00,000 --> 00:00:02,000\nAnna: Hej.\n"


class ExportJobRepository:
    """In-memory Conversion Hub job repository with export lookup support."""

    def __init__(self) -> None:
        self.jobs: dict[UUID, ConversionHubJob] = {}

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        return self.jobs.get(job_id)

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        for job in self.jobs.values():
            if job.upstream_job_id == upstream_job_id:
                return job
        return None

    async def get_latest_transcript_formatter_export(
        self,
        *,
        owner_user_id: UUID,
        input_filename: str,
    ) -> ConversionHubJob | None:
        matches = [
            job
            for job in self.jobs.values()
            if job.owner_user_id == owner_user_id
            and job.input_filename == input_filename
            and job.source_format is ConversionHubSourceFormatV2.TRANSCRIPT_JSON
            and job.output_format is ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE
        ]
        return max(matches, key=lambda job: job.updated_at, default=None)

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


class ExportArtifactRepository:
    """In-memory formatter artifact repository keyed like production storage."""

    def __init__(self) -> None:
        self.records: dict[
            tuple[UUID, UUID, ConversionHubTranscriptFormatterArtifactKey],
            ConversionHubTranscriptFormatterArtifactRecord,
        ] = {}

    async def replace_for_replay(
        self,
        *,
        records: list[ConversionHubTranscriptFormatterArtifactRecord],
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        if not records:
            return []
        owner_user_id = records[0].owner_user_id
        transcript_id = records[0].transcript_id
        await self.delete_for_transcript(
            owner_user_id=owner_user_id,
            transcript_id=transcript_id,
        )
        for record in records:
            self.records[(record.owner_user_id, record.transcript_id, record.artifact_key)] = record
        return records

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]:
        return [
            record
            for record in self.records.values()
            if record.owner_user_id == owner_user_id and record.transcript_id == transcript_id
        ]

    async def get_by_owner_transcript_and_key(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> ConversionHubTranscriptFormatterArtifactRecord | None:
        return self.records.get((owner_user_id, transcript_id, artifact_key))

    async def delete_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> None:
        self.records = {
            key: record
            for key, record in self.records.items()
            if not (record.owner_user_id == owner_user_id and record.transcript_id == transcript_id)
        }


class ExportStateRepository:
    """In-memory formatter export-state repository keyed by local job."""

    def __init__(self) -> None:
        self.records: dict[UUID, ConversionHubTranscriptFormatterExportStateRecord] = {}

    async def upsert(
        self,
        *,
        record: ConversionHubTranscriptFormatterExportStateRecord,
    ) -> ConversionHubTranscriptFormatterExportStateRecord:
        self.records[record.conversion_hub_job_id] = record
        return record

    async def get_by_job_id(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ConversionHubTranscriptFormatterExportStateRecord | None:
        record = self.records.get(conversion_hub_job_id)
        if record is None or record.owner_user_id != owner_user_id:
            return None
        return record


class FakeFormatterProducer:
    """Capture producer requests and return a configured task-363 result."""

    def __init__(
        self,
        result: ConversionHubTranscriptFormatterProducerResult | DomainError,
    ) -> None:
        self.result = result
        self.requests: list[ConversionHubTranscriptFormatterProducerRequest] = []

    async def create_transcript_formatter_export(
        self,
        *,
        request: ConversionHubTranscriptFormatterProducerRequest,
    ) -> ConversionHubTranscriptFormatterProducerResult:
        self.requests.append(request)
        if isinstance(self.result, DomainError):
            raise self.result
        return self.result


def saved_transcript(*, owner_user_id: UUID, transcript_id: UUID) -> ConversionHubSavedTranscript:
    return ConversionHubSavedTranscript(
        id=transcript_id,
        owner_user_id=owner_user_id,
        conversion_hub_job_id=uuid4(),
        sir_convert_job_id="sir-transcript-job-1",
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=NOW,
        correlation_id="corr-transcript-1",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {
                "text": "Hej. Valkommen.",
                "segments": [
                    {
                        "id": "seg_1",
                        "start_seconds": 0,
                        "end_seconds": 2,
                        "speaker_label": "SPEAKER_00",
                        "text": "Hej.",
                    },
                    {
                        "id": "seg_2",
                        "start_seconds": 3,
                        "end_seconds": 4,
                        "speaker_label": "SPEAKER_01",
                        "text": "Valkommen.",
                    },
                ],
            },
        },
        created_at=NOW,
        updated_at=NOW,
    )


def overlay(
    *,
    owner_user_id: UUID,
    transcript_id: UUID,
    canonical_speaker_label: str,
    display_name: str,
) -> ConversionHubTranscriptSpeakerOverlay:
    return ConversionHubTranscriptSpeakerOverlay(
        id=uuid4(),
        owner_user_id=owner_user_id,
        transcript_id=transcript_id,
        canonical_speaker_label=canonical_speaker_label,
        display_name=display_name,
        created_at=NOW,
        updated_at=NOW,
    )


async def seed_transcript(
    *,
    actor_id: UUID,
    transcript_id: UUID,
    transcripts: InMemorySavedTranscriptRepository,
    overlays: InMemoryTranscriptSpeakerOverlayRepository,
) -> None:
    transcripts.records[transcript_id] = saved_transcript(
        owner_user_id=actor_id,
        transcript_id=transcript_id,
    )
    await overlays.replace_for_transcript(
        owner_user_id=actor_id,
        transcript_id=transcript_id,
        overlays=[
            overlay(
                owner_user_id=actor_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Anna",
            ),
            overlay(
                owner_user_id=actor_id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_01",
                display_name="Bo",
            ),
        ],
    )


def producer_success(
    *,
    job_id: str = "sir-replay-job-1",
    artifacts: dict[ConversionHubTranscriptFormatterArtifactKey, bytes] | None = None,
) -> ConversionHubTranscriptFormatterProducerResult:
    artifact_bytes = artifacts or {
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: TXT,
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: MD,
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT: VTT,
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT: SRT,
    }
    return ConversionHubTranscriptFormatterProducerResult(
        sir_convert_job_id=job_id,
        status="succeeded",
        result=result_payload(job_id=job_id),
        artifact_manifest=artifact_manifest(job_id=job_id, artifacts=artifact_bytes),
        artifacts={
            artifact_key: ConversionHubTranscriptFormatterProducerArtifact(
                artifact_key=artifact_key,
                content_type=content_type(artifact_key),
                content=content,
            )
            for artifact_key, content in artifact_bytes.items()
        },
        error_message=None,
    )


def producer_status(
    *,
    status: str,
    job_id: str = "sir-replay-job-1",
    error_message: str | None = "Replay failed.",
) -> ConversionHubTranscriptFormatterProducerResult:
    return ConversionHubTranscriptFormatterProducerResult(
        sir_convert_job_id=job_id,
        status=status,
        result=None,
        artifact_manifest=None,
        artifacts={},
        error_message=error_message,
    )


def result_payload(*, job_id: str) -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "status": "succeeded",
        "result": {
            "artifact": {
                "filename": "transcript_replay_bundle_manifest.json",
                "format": "transcript_bundle",
                "content_type": "application/json",
                "size_bytes": 256,
                "sha256": "a" * 64,
            },
            "conversion_metadata": {
                "pipeline_used": "transcript_json_to_transcript_bundle_replay_v2",
                "options_fingerprint": "sha256:abc",
            },
            "warnings": [],
        },
    }


def artifact_manifest(
    *,
    job_id: str,
    artifacts: dict[ConversionHubTranscriptFormatterArtifactKey, bytes],
) -> dict[str, object]:
    return {
        "api_version": "v2",
        "job_id": job_id,
        "output_format": "transcript_bundle",
        "artifacts": [
            {
                "artifact_key": artifact_key.value,
                "availability": "available",
                "filename": filename(artifact_key),
                "content_type": content_type(artifact_key),
                "size_bytes": len(content),
                "sha256": sha256(content).hexdigest(),
                "retrieval_path": f"/v2/convert/jobs/{job_id}/artifacts/{artifact_key.value}",
            }
            for artifact_key, content in artifacts.items()
        ],
    }


def filename(artifact_key: ConversionHubTranscriptFormatterArtifactKey) -> str:
    return {
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: "transcript_txt.txt",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: "transcript_md.md",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT: "transcript_vtt.vtt",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT: "transcript_srt.srt",
    }[artifact_key]


def content_type(artifact_key: ConversionHubTranscriptFormatterArtifactKey) -> str:
    return {
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: "text/plain",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: "text/markdown",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_VTT: "text/vtt",
        ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_SRT: "application/x-subrip",
    }[artifact_key]


def handler(
    *,
    jobs: ExportJobRepository,
    transcripts: InMemorySavedTranscriptRepository,
    overlays: InMemoryTranscriptSpeakerOverlayRepository,
    artifacts: ExportArtifactRepository,
    producer: ConversionHubTranscriptFormatterProducerProtocol,
    ids: list[UUID],
    export_states: ExportStateRepository | None = None,
) -> export_handlers.RequestConversionHubTranscriptFormatterExportHandler:
    generated_ids = [*ids, *(uuid4() for _ in range(8))]
    return export_handlers.RequestConversionHubTranscriptFormatterExportHandler(
        jobs=jobs,
        transcripts=transcripts,
        speaker_overlays=overlays,
        artifacts=artifacts,
        export_states=export_states or ExportStateRepository(),
        producer=producer,
        uow=FakeUow(),
        clock=FixedClock(NOW),
        id_generator=SequentialIdGenerator(generated_ids),
    )


def assert_request_transcript_json(
    *,
    request: ConversionHubTranscriptFormatterProducerRequest,
    transcript_json: Mapping[str, object],
) -> None:
    assert json.loads(request.file_bytes.decode("utf-8")) == transcript_json
