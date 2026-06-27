"""Tests for product-owned transcript formatter exports.

Domain purpose:
  Prove Skriptoteket, not the browser, owns saved-transcript formatter export
  intent, Sir Convert producer submission, artifact verification, and product
  export state.

Relationships:
  - Exercises `conversion_hub_transcript_formatter_exports` handlers.
  - Uses in-memory repository/protocol fakes from the local export fixtures.
"""

from __future__ import annotations

from hashlib import sha256
from typing import cast
from uuid import uuid4

import httpx
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
from skriptoteket.application.curated_apps.conversion_hub_transcript_exports import (
    ConversionHubTranscriptFormatterExportRequest,
    ConversionHubTranscriptFormatterExportStatus,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_formatter_contracts import (
    ConversionHubTranscriptFormatterArtifactKey,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_exports as export_handlers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    sir_convert_transcript_formatter_producer as producer_client,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertClientSettingsV2,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import SirConvertJobStatusV2
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_export_fixtures as fx,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_transcript_saves import (
    InMemorySavedTranscriptRepository,
    InMemoryTranscriptSpeakerOverlayRepository,
)


class TransportFailingHttpClient:
    """Fake httpx client that simulates producer transport failure."""

    async def post(self, *_args: object, **_kwargs: object) -> httpx.Response:
        request = httpx.Request("POST", "https://sir-convert.local/v2/convert/jobs")
        raise httpx.ConnectError("connection refused", request=request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_calls_producer_and_persists_verified_artifacts() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    artifact_ids = [uuid4(), uuid4(), uuid4(), uuid4()]
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer = fx.FakeFormatterProducer(fx.producer_success())
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id, *artifact_ids],
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(),
        correlation_id="corr-export-1",
    )

    assert result.status is ConversionHubTranscriptFormatterExportStatus.SUCCEEDED
    assert result.conversion_hub_job_id == local_job_id
    assert [artifact.artifact_key for artifact in result.artifacts] == [
        "transcript_txt",
        "transcript_md",
        "transcript_vtt",
        "transcript_srt",
    ]
    assert len(producer.requests) == 1
    producer_request = producer.requests[0]
    assert producer_request.filename == "saved-transcript.json"
    assert producer_request.content_type == "application/json"
    assert producer_request.wait_seconds == 0
    assert producer_request.correlation_id == "corr-export-1"
    assert producer_request.job_spec["source"] == {
        "kind": "upload",
        "filename": "saved-transcript.json",
        "format": "transcript_json",
    }
    assert producer_request.job_spec["transcript_formatter_options"] == {
        "schema_version": "transcript_formatter_replay_v1",
        "requested_artifacts": ["txt", "md", "vtt", "srt"],
        "speaker_label_overrides": [
            {"canonical_speaker_label": "SPEAKER_00", "display_name": "Anna"},
            {"canonical_speaker_label": "SPEAKER_01", "display_name": "Bo"},
        ],
    }
    fx.assert_request_transcript_json(
        request=producer_request,
        transcript_json=transcripts.records[transcript_id].transcript_json,
    )
    assert jobs.jobs[local_job_id].status is ConversionHubJobStatus.SUCCEEDED
    assert jobs.jobs[local_job_id].input_filename == f"saved-transcript-{transcript_id}.json"
    assert {record.content for record in artifacts.records.values()} == {
        fx.TXT,
        fx.MD,
        fx.VTT,
        fx.SRT,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_rejects_partial_speaker_overlays_before_producer_submission() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer = fx.FakeFormatterProducer(fx.producer_success())
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )
    await overlays.replace_for_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
        overlays=[
            fx.overlay(
                owner_user_id=actor.id,
                transcript_id=transcript_id,
                canonical_speaker_label="SPEAKER_00",
                display_name="Anna",
            ),
        ],
    )

    with pytest.raises(DomainError) as exc:
        await fx.handler(
            jobs=jobs,
            transcripts=transcripts,
            overlays=overlays,
            artifacts=artifacts,
            producer=producer,
            ids=[local_job_id],
        ).handle(
            actor=actor,
            transcript_id=transcript_id,
            request=ConversionHubTranscriptFormatterExportRequest(),
            correlation_id="corr-export-1",
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR
    assert producer.requests == []
    assert jobs.jobs == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_succeeded_export_state_preserves_requested_artifacts_for_post_and_get() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    export_states = fx.ExportStateRepository()
    producer = fx.FakeFormatterProducer(
        fx.producer_success(
            artifacts={
                ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: fx.MD,
            }
        )
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    post_result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
        export_states=export_states,
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(requested_artifacts=["md"]),
        correlation_id="corr-export-1",
    )
    get_result = await export_handlers.GetConversionHubTranscriptFormatterExportHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        export_states=export_states,
        uow=FakeUow(),
    ).handle(actor=actor, transcript_id=transcript_id)

    assert post_result.status is ConversionHubTranscriptFormatterExportStatus.SUCCEEDED
    assert post_result.requested_artifacts == ["md"]
    assert [artifact.artifact_key for artifact in post_result.artifacts] == ["transcript_md"]
    assert get_result.status is ConversionHubTranscriptFormatterExportStatus.SUCCEEDED
    assert get_result.requested_artifacts == ["md"]
    assert [artifact.artifact_key for artifact in get_result.artifacts] == ["transcript_md"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_records_failed_terminal_state_without_artifact_rows() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer = fx.FakeFormatterProducer(
        fx.producer_status(
            status=SirConvertJobStatusV2.FAILED,
            error_message="formatter execution failed",
        ),
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(),
        correlation_id="corr-export-1",
    )

    assert result.status is ConversionHubTranscriptFormatterExportStatus.FAILED
    assert result.error_message == "Filerna kunde inte skapas. Försök igen."
    assert result.artifacts == []
    assert jobs.jobs[local_job_id].status is ConversionHubJobStatus.FAILED
    assert artifacts.records == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_maps_producer_transport_failure_to_failed_state() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer = producer_client.SirConvertTranscriptFormatterProducerV2(
        settings=SirConvertClientSettingsV2(
            base_url="https://sir-convert.local",
            api_key="test-key",
            timeout_seconds=1.0,
        ),
        client=cast(httpx.AsyncClient, TransportFailingHttpClient()),
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(requested_artifacts=["txt"]),
        correlation_id="corr-export-transport",
    )

    assert result.status is ConversionHubTranscriptFormatterExportStatus.FAILED
    assert result.requested_artifacts == ["txt"]
    assert result.error_message == "Filerna kunde inte skapas. Försök igen."
    assert jobs.jobs[local_job_id].status is ConversionHubJobStatus.FAILED
    assert artifacts.records == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_records_pending_state_without_fake_artifacts() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer = fx.FakeFormatterProducer(
        fx.producer_status(status=SirConvertJobStatusV2.QUEUED, error_message=None)
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(),
        correlation_id="corr-export-1",
    )

    assert result.status is ConversionHubTranscriptFormatterExportStatus.PENDING
    assert result.artifacts == []
    assert jobs.jobs[local_job_id].status is ConversionHubJobStatus.QUEUED
    assert artifacts.records == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pending_export_state_preserves_requested_artifacts_for_post_and_get() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    export_states = fx.ExportStateRepository()
    producer = fx.FakeFormatterProducer(
        fx.producer_status(status=SirConvertJobStatusV2.RUNNING, error_message=None)
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    post_result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
        export_states=export_states,
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(requested_artifacts=["txt", "md"]),
        correlation_id="corr-export-1",
    )
    get_result = await export_handlers.GetConversionHubTranscriptFormatterExportHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        export_states=export_states,
        uow=FakeUow(),
    ).handle(actor=actor, transcript_id=transcript_id)

    assert post_result.status is ConversionHubTranscriptFormatterExportStatus.RUNNING
    assert post_result.requested_artifacts == ["txt", "md"]
    assert post_result.artifacts == []
    assert get_result.status is ConversionHubTranscriptFormatterExportStatus.RUNNING
    assert get_result.requested_artifacts == ["txt", "md"]
    assert get_result.artifacts == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_failed_export_state_preserves_requested_artifacts_for_post_and_get() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    export_states = fx.ExportStateRepository()
    producer = fx.FakeFormatterProducer(
        fx.producer_status(
            status=SirConvertJobStatusV2.FAILED,
            error_message="formatter execution failed",
        ),
    )
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    post_result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
        export_states=export_states,
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(requested_artifacts=["vtt"]),
        correlation_id="corr-export-1",
    )
    get_result = await export_handlers.GetConversionHubTranscriptFormatterExportHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        export_states=export_states,
        uow=FakeUow(),
    ).handle(actor=actor, transcript_id=transcript_id)

    assert post_result.status is ConversionHubTranscriptFormatterExportStatus.FAILED
    assert post_result.requested_artifacts == ["vtt"]
    assert post_result.artifacts == []
    assert get_result.status is ConversionHubTranscriptFormatterExportStatus.FAILED
    assert get_result.requested_artifacts == ["vtt"]
    assert get_result.artifacts == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_product_export_fails_closed_for_missing_or_bad_artifact_authority() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    overlays = InMemoryTranscriptSpeakerOverlayRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    producer_result = fx.producer_success(
        artifacts={
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_TXT: fx.TXT,
            ConversionHubTranscriptFormatterArtifactKey.TRANSCRIPT_MD: fx.MD,
        }
    )
    producer = fx.FakeFormatterProducer(producer_result)
    await fx.seed_transcript(
        actor_id=actor.id,
        transcript_id=transcript_id,
        transcripts=transcripts,
        overlays=overlays,
    )

    result = await fx.handler(
        jobs=jobs,
        transcripts=transcripts,
        overlays=overlays,
        artifacts=artifacts,
        producer=producer,
        ids=[local_job_id],
    ).handle(
        actor=actor,
        transcript_id=transcript_id,
        request=ConversionHubTranscriptFormatterExportRequest(),
        correlation_id="corr-export-1",
    )

    assert result.status is ConversionHubTranscriptFormatterExportStatus.FAILED
    assert jobs.jobs[local_job_id].status is ConversionHubJobStatus.FAILED
    assert artifacts.records == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_product_export_state_uses_local_job_and_artifacts_only() -> None:
    actor = make_user()
    transcript_id = uuid4()
    local_job_id = uuid4()
    artifact_id = uuid4()
    transcripts = InMemorySavedTranscriptRepository()
    jobs = fx.ExportJobRepository()
    artifacts = fx.ExportArtifactRepository()
    transcripts.records[transcript_id] = fx.saved_transcript(
        owner_user_id=actor.id,
        transcript_id=transcript_id,
    )
    await jobs.create(
        job=ConversionHubJob(
            id=local_job_id,
            owner_user_id=actor.id,
            input_filename=f"saved-transcript-{transcript_id}.json",
            source_format=ConversionHubSourceFormatV2.TRANSCRIPT_JSON,
            output_format=ConversionHubOutputFormatV2.TRANSCRIPT_BUNDLE,
            pdf_layout=None,
            upstream_job_id="sir-export-job-1",
            status=ConversionHubJobStatus.SUCCEEDED,
            correlation_id="corr-export-1",
            error_message=None,
            created_at=fx.NOW,
            updated_at=fx.NOW,
        )
    )
    await artifacts.replace_for_export(
        records=[
            ConversionHubTranscriptFormatterArtifactRecord(
                id=artifact_id,
                owner_user_id=actor.id,
                transcript_id=transcript_id,
                conversion_hub_job_id=local_job_id,
                sir_convert_job_id="sir-export-job-1",
                requested_artifact="txt",
                artifact_key="transcript_txt",
                filename="transcript_txt.txt",
                content_type="text/plain",
                size_bytes=len(fx.TXT),
                sha256=sha256(fx.TXT).hexdigest(),
                retrieval_path="/v2/convert/jobs/sir-export-job-1/artifacts/transcript_txt",
                content=fx.TXT,
                created_at=fx.NOW,
                updated_at=fx.NOW,
            )
        ],
    )
    handler = export_handlers.GetConversionHubTranscriptFormatterExportHandler(
        jobs=jobs,
        transcripts=transcripts,
        artifacts=artifacts,
        export_states=fx.ExportStateRepository(),
        uow=FakeUow(),
    )

    result = await handler.handle(actor=actor, transcript_id=transcript_id)

    assert result.status is ConversionHubTranscriptFormatterExportStatus.SUCCEEDED
    assert result.conversion_hub_job_id == local_job_id
    assert result.artifacts[0].artifact_key == "transcript_txt"
    assert set(result.model_dump()) == {
        "transcript_id",
        "conversion_hub_job_id",
        "status",
        "requested_artifacts",
        "artifacts",
        "error_message",
        "created_at",
        "updated_at",
    }
