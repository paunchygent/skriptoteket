"""Integration tests for durable Conversion Hub transcript persistence.

Domain purpose:
  Prove PR-0343 stores canonical transcript JSON with owner/job provenance so
  later transcript management can read saved data after Sir Convert TTLs.

Relationships:
  - Exercises `PostgreSQLConversionHubSavedTranscriptRepository`.
  - Uses the Conversion Hub job ledger as the owner-scoped parent resource.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscript,
    ConversionHubTranscriptSpeakerOverlay,
)
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.repositories.conversion_hub_saved_transcripts import (
    PostgreSQLConversionHubSavedTranscriptRepository,
    PostgreSQLConversionHubTranscriptSpeakerOverlayRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _create_user(db_session: AsyncSession, *, email_prefix: str) -> UUID:
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    db_session.add(
        UserModel(
            id=user_id,
            email=f"{email_prefix}-{user_id.hex[:8]}@example.com",
            password_hash="hash",
            role=Role.USER,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return user_id


async def _create_transcript_job(
    db_session: AsyncSession,
    *,
    owner_user_id: UUID,
    upstream_job_id: str,
) -> UUID:
    now = datetime.now(timezone.utc)
    job_id = uuid4()
    db_session.add(
        ConversionHubJobModel(
            id=job_id,
            owner_user_id=owner_user_id,
            input_filename="seminarium.m4a",
            source_format="audio",
            output_format="transcript_bundle",
            upstream_job_id=upstream_job_id,
            status="succeeded",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return job_id


def _record(
    *,
    owner_user_id: UUID,
    conversion_hub_job_id: UUID,
    sir_convert_job_id: str,
) -> ConversionHubSavedTranscript:
    now = datetime(2026, 6, 12, 10, 5, tzinfo=timezone.utc)
    return ConversionHubSavedTranscript(
        id=uuid4(),
        owner_user_id=owner_user_id,
        conversion_hub_job_id=conversion_hub_job_id,
        sir_convert_job_id=sir_convert_job_id,
        artifact_key="transcript_json",
        source_filename="seminarium.m4a",
        transcript_schema_version="transcript_json_v1",
        language_code="sv",
        diarization_mode="known_speaker_count",
        speaker_count=2,
        speaker_min=None,
        speaker_max=None,
        generated_at=datetime(2026, 6, 12, 10, 0, tzinfo=timezone.utc),
        correlation_id="corr-transcript-1",
        transcript_json={
            "schema_version": "transcript_json_v1",
            "transcript": {
                "text": "Hej från seminariet.",
                "segments": [
                    {
                        "id": "seg_1",
                        "start_seconds": 0,
                        "end_seconds": 2.4,
                        "speaker_label": "SPEAKER_00",
                        "text": "Hej från seminariet.",
                    }
                ],
            },
        },
        created_at=now,
        updated_at=now,
    )


def _first_segment_speaker_label(record: ConversionHubSavedTranscript) -> str:
    transcript = record.transcript_json["transcript"]
    assert isinstance(transcript, dict)
    segments = transcript["segments"]
    assert isinstance(segments, list)
    first_segment = segments[0]
    assert isinstance(first_segment, dict)
    speaker_label = first_segment["speaker_label"]
    assert isinstance(speaker_label, str)
    return speaker_label


@pytest.mark.integration
async def test_saved_transcript_roundtrip_preserves_json_and_provenance(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="transcript-owner")
    job_id = await _create_transcript_job(
        db_session,
        owner_user_id=owner_id,
        upstream_job_id="sir-transcript-job-1",
    )
    repo = PostgreSQLConversionHubSavedTranscriptRepository(db_session)

    saved = await repo.create(
        record=_record(
            owner_user_id=owner_id,
            conversion_hub_job_id=job_id,
            sir_convert_job_id="sir-transcript-job-1",
        )
    )
    readback = await repo.get_by_owner_and_upstream_job(
        owner_user_id=owner_id,
        sir_convert_job_id="sir-transcript-job-1",
    )

    assert readback is not None
    assert saved.id == readback.id
    assert readback.conversion_hub_job_id == job_id
    assert _first_segment_speaker_label(readback) == "SPEAKER_00"

    owner_readback = await repo.get_by_owner_and_id(
        owner_user_id=owner_id,
        transcript_id=saved.id,
    )
    other_owner_id = await _create_user(db_session, email_prefix="transcript-other-owner")
    other_owner_readback = await repo.get_by_owner_and_id(
        owner_user_id=other_owner_id,
        transcript_id=saved.id,
    )
    assert owner_readback == readback
    assert other_owner_readback is None


@pytest.mark.integration
async def test_owner_upstream_uniqueness_prevents_duplicate_saves(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="transcript-duplicate")
    job_id = await _create_transcript_job(
        db_session,
        owner_user_id=owner_id,
        upstream_job_id="sir-transcript-job-duplicate",
    )
    repo = PostgreSQLConversionHubSavedTranscriptRepository(db_session)
    await repo.create(
        record=_record(
            owner_user_id=owner_id,
            conversion_hub_job_id=job_id,
            sir_convert_job_id="sir-transcript-job-duplicate",
        )
    )

    with pytest.raises(IntegrityError):
        await repo.create(
            record=_record(
                owner_user_id=owner_id,
                conversion_hub_job_id=job_id,
                sir_convert_job_id="sir-transcript-job-duplicate",
            )
        )


@pytest.mark.integration
async def test_speaker_overlays_replace_and_clear_for_saved_transcript(
    db_session: AsyncSession,
) -> None:
    owner_id = await _create_user(db_session, email_prefix="transcript-overlay-owner")
    job_id = await _create_transcript_job(
        db_session,
        owner_user_id=owner_id,
        upstream_job_id="sir-transcript-job-overlay",
    )
    transcript_repo = PostgreSQLConversionHubSavedTranscriptRepository(db_session)
    overlay_repo = PostgreSQLConversionHubTranscriptSpeakerOverlayRepository(db_session)
    saved = await transcript_repo.create(
        record=_record(
            owner_user_id=owner_id,
            conversion_hub_job_id=job_id,
            sir_convert_job_id="sir-transcript-job-overlay",
        )
    )
    now = datetime(2026, 6, 12, 11, 0, tzinfo=timezone.utc)

    first_result = await overlay_repo.replace_for_transcript(
        owner_user_id=owner_id,
        transcript_id=saved.id,
        overlays=[
            ConversionHubTranscriptSpeakerOverlay(
                id=uuid4(),
                owner_user_id=owner_id,
                transcript_id=saved.id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Anna Andersson",
                created_at=now,
                updated_at=now,
            )
        ],
    )
    second_result = await overlay_repo.replace_for_transcript(
        owner_user_id=owner_id,
        transcript_id=saved.id,
        overlays=[
            ConversionHubTranscriptSpeakerOverlay(
                id=uuid4(),
                owner_user_id=owner_id,
                transcript_id=saved.id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Bo Berg",
                created_at=now,
                updated_at=now,
            )
        ],
    )
    cleared = await overlay_repo.replace_for_transcript(
        owner_user_id=owner_id,
        transcript_id=saved.id,
        overlays=[],
    )

    assert [overlay.display_name for overlay in first_result] == ["Anna Andersson"]
    assert [overlay.display_name for overlay in second_result] == ["Bo Berg"]
    assert cleared == []
