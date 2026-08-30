"""Protocols for the Conversion Hub curated app.

Purpose:
  Provide typed persistence seams for Conversion Hub's locally owned job ledger
  and transcript formatter producer boundary so the application layer can own
  job identity, export state, and artifact authorization without coupling to
  infrastructure details.

Relationships:
  - Used by `application.curated_apps.handlers.conversion_hub_jobs`.
  - Implemented by `infrastructure.repositories.conversion_hub_jobs`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJob
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportStateRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_formatter_contracts import (
    ConversionHubTranscriptFormatterArtifactFormat,
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2


class ConversionHubJobRepositoryProtocol(Protocol):
    """Persist local Conversion Hub jobs."""

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob: ...

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None: ...

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None: ...

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob: ...


class ExamConverterSubmissionRepositoryProtocol(Protocol):
    """Conversion job repository with native Exam Converter submission lookup."""

    async def get_by_owner_and_submission_key(
        self,
        *,
        owner_user_id: UUID,
        submission_idempotency_key: str,
    ) -> ConversionHubJob | None: ...


class ConversionHubTranscriptFormatterExportJobRepositoryProtocol(Protocol):
    """Read product-owned formatter export jobs."""

    async def get_latest_transcript_formatter_export(
        self,
        *,
        owner_user_id: UUID,
        input_filename: str,
    ) -> ConversionHubJob | None: ...


class ConversionHubSavedTranscriptRepositoryProtocol(Protocol):
    """Persist owner-scoped canonical transcript JSON records."""

    async def create(
        self,
        *,
        record: ConversionHubSavedTranscript,
    ) -> ConversionHubSavedTranscript: ...

    async def get_by_owner_and_id(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> ConversionHubSavedTranscript | None: ...

    async def get_by_owner_and_upstream_job(
        self,
        *,
        owner_user_id: UUID,
        sir_convert_job_id: str,
    ) -> ConversionHubSavedTranscript | None: ...


class ConversionHubTranscriptSpeakerOverlayRepositoryProtocol(Protocol):
    """Persist owner-scoped speaker display-name overlays for transcripts."""

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptSpeakerOverlay]: ...

    async def replace_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        overlays: list[ConversionHubTranscriptSpeakerOverlay],
    ) -> list[ConversionHubTranscriptSpeakerOverlay]: ...


class ConversionHubTranscriptFormatterArtifactRepositoryProtocol(Protocol):
    """Persist producer-returned transcript formatter artifact references."""

    async def replace_for_export(
        self,
        *,
        records: list[ConversionHubTranscriptFormatterArtifactRecord],
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]: ...

    async def get_by_owner_transcript_and_key(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
        artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    ) -> ConversionHubTranscriptFormatterArtifactRecord | None: ...

    async def delete_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> None: ...


class ConversionHubTranscriptFormatterExportArtifactRepositoryProtocol(Protocol):
    """Read product-owned formatter artifact refs for export state."""

    async def list_for_transcript(
        self,
        *,
        owner_user_id: UUID,
        transcript_id: UUID,
    ) -> list[ConversionHubTranscriptFormatterArtifactRecord]: ...


class ConversionHubTranscriptFormatterExportStateRepositoryProtocol(Protocol):
    """Persist requested formatter artifacts for every product export state."""

    async def upsert(
        self,
        *,
        record: ConversionHubTranscriptFormatterExportStateRecord,
    ) -> ConversionHubTranscriptFormatterExportStateRecord: ...

    async def get_by_job_id(
        self,
        *,
        owner_user_id: UUID,
        conversion_hub_job_id: UUID,
    ) -> ConversionHubTranscriptFormatterExportStateRecord | None: ...


@dataclass(frozen=True, slots=True)
class ConversionHubTranscriptFormatterProducerRequest:
    """Server-owned task-363 producer request for saved transcript exports."""

    filename: str
    content_type: str
    file_bytes: bytes
    job_spec: dict[str, object]
    requested_artifacts: tuple[ConversionHubTranscriptFormatterArtifactFormat, ...]
    idempotency_key: str
    correlation_id: str | None
    wait_seconds: int


@dataclass(frozen=True, slots=True)
class ConversionHubTranscriptFormatterProducerArtifact:
    """Downloaded producer bytes for one named formatter artifact."""

    artifact_key: ConversionHubTranscriptFormatterArtifactKey
    content_type: str
    content: bytes


@dataclass(frozen=True, slots=True)
class ConversionHubTranscriptFormatterProducerResult:
    """Terminal or observed producer result returned to the application handler."""

    sir_convert_job_id: str | None
    status: SirConvertJobStatusV2
    result: dict[str, object] | None
    artifact_manifest: dict[str, object] | None
    artifacts: dict[
        ConversionHubTranscriptFormatterArtifactKey,
        ConversionHubTranscriptFormatterProducerArtifact,
    ]
    error_message: str | None


class ConversionHubTranscriptFormatterProducerProtocol(Protocol):
    """Submit saved transcript JSON to the accepted Sir Convert formatter producer."""

    async def create_transcript_formatter_export(
        self,
        *,
        request: ConversionHubTranscriptFormatterProducerRequest,
    ) -> ConversionHubTranscriptFormatterProducerResult: ...
