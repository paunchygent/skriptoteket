"""Tests for Conversion Hub transcript formatter artifact actions.

Domain purpose:
  Prove overlay-aware transcript formatter artifacts can be downloaded and
  saved only from owner-scoped replay provenance recorded by Skriptoteket.

Relationships:
  - Exercises `handlers.conversion_hub_transcript_artifact_actions`.
  - Reuses PR-0347 replay job and saved-transcript fixtures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

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
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_artifact_actions as artifact_action_handlers,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind, VaultUsage
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers import (
    test_conversion_hub_transcript_formatter_replay as replay_fixtures,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    FixedClock,
    FixedIdGenerator,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
)


class InMemoryTranscriptFormatterArtifactRepository:
    """In-memory formatter artifact refs keyed like the production repository."""

    def __init__(self) -> None:
        self.records: dict[
            tuple[UUID, UUID, ConversionHubTranscriptFormatterArtifactKey],
            (ConversionHubTranscriptFormatterArtifactRecord),
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


def _settings(*, max_file_bytes: int = 1_000_000, max_total_bytes: int = 2_000_000) -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=max_file_bytes,
        VAULT_MAX_TOTAL_BYTES=max_total_bytes,
    )


def _replay_job(*, owner_user_id: UUID, job_id: UUID, transcript_id: UUID) -> ConversionHubJob:
    now = datetime(2026, 6, 13, 12, 0, tzinfo=timezone.utc)
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename=f"saved-transcript-{transcript_id}.json",
        source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
        output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-replay-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-replay-1",
        error_message=None,
        created_at=now,
        updated_at=now,
    )


def _artifact_record(
    *,
    owner_user_id: UUID,
    transcript_id: UUID,
    conversion_hub_job_id: UUID,
    content: bytes | None,
) -> ConversionHubTranscriptFormatterArtifactRecord:
    actual_content = content or b""
    now = datetime(2026, 6, 13, 12, 1, tzinfo=timezone.utc)
    return ConversionHubTranscriptFormatterArtifactRecord(
        id=uuid4(),
        owner_user_id=owner_user_id,
        transcript_id=transcript_id,
        conversion_hub_job_id=conversion_hub_job_id,
        sir_convert_job_id="sir-replay-job-1",
        requested_artifact="txt",
        artifact_key="transcript_txt",
        filename="producer-transcript.txt",
        content_type="text/plain",
        size_bytes=len(actual_content),
        sha256=sha256(actual_content).hexdigest(),
        retrieval_path="/v2/convert/jobs/sir-replay-job-1/artifacts/transcript_txt",
        content=content,
        created_at=now,
        updated_at=now,
    )


async def _seed_provenance(
    *,
    actor_id: UUID,
    content: bytes | None,
) -> tuple[
    UUID,
    InMemoryConversionHubJobRepository,
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptFormatterArtifactRepository,
]:
    transcript_id = uuid4()
    replay_job_id = uuid4()
    jobs = InMemoryConversionHubJobRepository()
    jobs.jobs[replay_job_id] = _replay_job(
        owner_user_id=actor_id,
        job_id=replay_job_id,
        transcript_id=transcript_id,
    )
    transcripts = InMemorySavedTranscriptRepository()
    transcripts.records[transcript_id] = replay_fixtures._saved_transcript(
        owner_user_id=actor_id,
        transcript_id=transcript_id,
    )
    artifacts = InMemoryTranscriptFormatterArtifactRepository()
    await artifacts.replace_for_replay(
        records=[
            _artifact_record(
                owner_user_id=actor_id,
                transcript_id=transcript_id,
                conversion_hub_job_id=replay_job_id,
                content=content,
            )
        ],
    )
    return transcript_id, jobs, transcripts, artifacts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_uses_persisted_replay_artifact_ref_with_product_filename() -> None:
    actor = make_user()
    content = b"overlay-aware transcript\n"
    transcript_id, jobs, transcripts, artifacts = await _seed_provenance(
        actor_id=actor.id,
        content=content,
    )
    handler = artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        uow=FakeUow(),
    )

    result = await handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        correlation_id="corr-download-1",
    )

    assert result.content == content
    assert result.content_type == "text/plain"
    assert result.filename == f"transkript-{transcript_id.hex[:8]}.txt"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_rejects_ref_only_artifact_without_persisted_content() -> None:
    actor = make_user()
    transcript_id, jobs, transcripts, artifacts = await _seed_provenance(
        actor_id=actor.id,
        content=None,
    )
    handler = artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            transcript_id=transcript_id,
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            correlation_id="corr-download-1",
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_downloads_producer_artifact_and_saves_app_export_to_mina_filer() -> None:
    actor = make_user()
    file_id = uuid4()
    content = b"overlay-aware transcript\n"
    transcript_id, jobs, transcripts, artifacts = await _seed_provenance(
        actor_id=actor.id,
        content=content,
    )
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_files.create.side_effect = lambda *, file: file
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_usage.get_for_update.return_value = VaultUsage(
        user_id=actor.id,
        bytes_total=10,
        updated_at=datetime(2026, 6, 13, tzinfo=timezone.utc),
    )
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    handler = artifact_action_handlers.SaveConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 13, 12, 5, tzinfo=timezone.utc)),
        id_generator=FixedIdGenerator(file_id),
        settings=_settings(),
    )

    result = await handler.handle(
        actor=actor,
        transcript_id=transcript_id,
        artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
        correlation_id="corr-save-1",
    )

    saved_file = vault_files.create.call_args.kwargs["file"]
    replay_job_id = next(iter(jobs.jobs.keys()))
    assert isinstance(saved_file, VaultFile)
    assert saved_file.user_id == actor.id
    assert saved_file.name == f"transkript-{transcript_id.hex[:8]}.txt"
    assert saved_file.source_kind is VaultFileSourceKind.APP_EXPORT
    assert saved_file.source_artifact_id == (
        f"documents.conversion_hub:transcript-replay:{replay_job_id}:transcript_txt"
    )
    vault_storage.store_file.assert_awaited_once_with(
        user_id=actor.id,
        file_id=file_id,
        content=content,
    )
    assert result.vault_artifact.file_id == file_id
    assert result.vault_artifact.name == f"transkript-{transcript_id.hex[:8]}.txt"
    assert result.source_artifact_id == saved_file.source_artifact_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_actions_fail_closed_without_persisted_replay_artifact_ref() -> None:
    actor = make_user()
    transcript_id, jobs, transcripts, _artifacts = await _seed_provenance(
        actor_id=actor.id,
        content=b"overlay-aware transcript\n",
    )
    handler = artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=InMemoryTranscriptFormatterArtifactRepository(),
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            transcript_id=transcript_id,
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            correlation_id="corr-download-1",
        )

    assert exc.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_actions_fail_closed_for_other_owner_and_wrong_replay_job() -> None:
    owner = make_user()
    other_user = make_user()
    content = b"overlay-aware transcript\n"
    transcript_id, jobs, transcripts, artifacts = await _seed_provenance(
        actor_id=owner.id,
        content=content,
    )
    handler = artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as owner_exc:
        await handler.handle(
            actor=other_user,
            transcript_id=transcript_id,
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            correlation_id="corr-download-1",
        )
    assert owner_exc.value.code is ErrorCode.NOT_FOUND

    replay_job = next(iter(jobs.jobs.values()))
    jobs.jobs[replay_job.id] = replay_job.model_copy(
        update={"input_filename": f"saved-transcript-{uuid4()}.json"}
    )
    with pytest.raises(DomainError) as provenance_exc:
        await handler.handle(
            actor=owner,
            transcript_id=transcript_id,
            artifact_key=ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT,
            correlation_id="corr-download-1",
        )
    assert provenance_exc.value.code is ErrorCode.VALIDATION_ERROR
