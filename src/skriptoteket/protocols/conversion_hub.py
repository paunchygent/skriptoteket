"""Protocols for the Conversion Hub curated app.

Purpose:
  Provide typed persistence seams for Conversion Hub's locally owned job ledger
  so the application layer can own job identity, status refresh, and artifact
  authorization without coupling to infrastructure details.

Relationships:
  - Used by `application.curated_apps.handlers.conversion_hub_jobs`.
  - Implemented by `infrastructure.repositories.conversion_hub_jobs`.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJob
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    ConversionHubTranscriptFormatterArtifactRecord,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)


class ConversionHubJobRepositoryProtocol(Protocol):
    """Persist local Conversion Hub jobs."""

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob: ...

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None: ...

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None: ...

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob: ...


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
    """Persist replay-returned transcript formatter artifact references."""

    async def replace_for_replay(
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
