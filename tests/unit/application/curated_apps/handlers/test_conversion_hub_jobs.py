"""Behavioral tests for the Conversion Hub local job handlers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubPdfLayoutV2,
    ConversionHubPdfOrientationV2,
    ConversionHubPdfPaperSizeV2,
    ConversionHubSourceFormatV2,
    RegisterExamConverterConversionHubJobRequest,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
    CreateConversionHubJobsHandler,
    DownloadConversionHubArtifactHandler,
    GetConversionHubJobHandler,
    RegisterExamConverterConversionHubJobHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertArtifactV2,
    SirConvertJobStatusV2,
    SirConvertJobV2,
    SirConvertSubmitRequestV2,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user


class InMemoryConversionHubJobRepository:
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

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        self.jobs[job.id] = job
        return job


@dataclass
class SequenceClock:
    current: datetime

    def now(self) -> datetime:
        value = self.current
        self.current = self.current + timedelta(seconds=1)
        return value


class SequenceIdGenerator:
    def __init__(self, ids: list[UUID]) -> None:
        self._ids = ids

    def new_uuid(self) -> UUID:
        return self._ids.pop(0)


class FakeSirConvertClient:
    def __init__(self) -> None:
        self.submit_results: list[SirConvertSubmittedJobV2 | DomainError] = []
        self.jobs_by_upstream_id: dict[str, SirConvertJobV2 | DomainError] = {}
        self.artifacts_by_upstream_id: dict[str, SirConvertArtifactOutcomeV2] = {}

    async def extract_text_direct(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        correlation_id: str | None = None,
    ) -> str:
        del file_bytes, filename, correlation_id
        raise NotImplementedError

    async def submit_job(
        self,
        *,
        request: SirConvertSubmitRequestV2,
    ) -> SirConvertSubmittedJobV2:
        del request
        result = self.submit_results.pop(0)
        if isinstance(result, DomainError):
            raise result
        return result

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2:
        del correlation_id
        result = self.jobs_by_upstream_id[job_id]
        if isinstance(result, DomainError):
            raise result
        return result

    async def download_artifact(
        self,
        job_id: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2:
        del correlation_id
        return self.artifacts_by_upstream_id[job_id]

    async def download_named_artifact(
        self,
        job_id: str,
        artifact_key: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2:
        del artifact_key, correlation_id
        return self.artifacts_by_upstream_id[job_id]

    async def create_webhook_subscription(
        self,
        *,
        callback_url: str,
        event_types: list[str],
        correlation_id: str | None,
    ) -> SirConvertWebhookSubscriptionV2:
        del callback_url, event_types, correlation_id
        raise NotImplementedError

    async def list_webhook_subscriptions(
        self,
        *,
        correlation_id: str | None,
    ) -> list[SirConvertWebhookSubscriptionSummaryV2]:
        del correlation_id
        raise NotImplementedError

    async def delete_webhook_subscription(
        self,
        subscription_id: str,
        *,
        correlation_id: str | None,
    ) -> None:
        del subscription_id, correlation_id
        raise NotImplementedError


def _pdf_spec() -> ConversionHubJobSpecV2:
    return ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
        pdf_layout=ConversionHubPdfLayoutV2(
            paper_size=ConversionHubPdfPaperSizeV2.A4,
            orientation=ConversionHubPdfOrientationV2.PORTRAIT,
            margins_mm=12,
        ),
    )


def _build_job_spec(*, spec: ConversionHubJobSpecV2, filename: str) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": spec.source_format.value},
        "conversion": {"output_format": spec.output_format.value},
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_exam_converter_job_creates_local_owned_job_for_upstream_id() -> None:
    actor = make_user()
    local_job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    handler = RegisterExamConverterConversionHubJobHandler(
        jobs=repo,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 5, 19, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([local_job_id]),
    )

    result = await handler.handle(
        actor=actor,
        request=RegisterExamConverterConversionHubJobRequest(
            correlation_id="corr-exam",
            input_filename="prov.dxe",
            status=ConversionHubJobStatus.SUCCEEDED,
            upstream_job_id="sir-job-1",
        ),
    )

    assert result.job_id == local_job_id
    assert result.upstream_job_id == "sir-job-1"
    assert repo.jobs[local_job_id].owner_user_id == actor.id
    assert repo.jobs[local_job_id].source_format is ConversionHubSourceFormatV2.DIGIEXAM_DXE
    assert repo.jobs[local_job_id].output_format is ConversionHubOutputFormatV2.EXAMNET_BUNDLE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_exam_converter_job_reuses_owned_existing_upstream_id() -> None:
    actor = make_user()
    local_job_id = uuid4()
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[local_job_id] = ConversionHubJob(
        id=local_job_id,
        owner_user_id=actor.id,
        input_filename="prov.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-exam",
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    handler = RegisterExamConverterConversionHubJobHandler(
        jobs=repo,
        uow=FakeUow(),
        clock=SequenceClock(now),
        id_generator=SequenceIdGenerator([uuid4()]),
    )

    result = await handler.handle(
        actor=actor,
        request=RegisterExamConverterConversionHubJobRequest(
            correlation_id="corr-exam",
            input_filename="prov.dxe",
            upstream_job_id="sir-job-1",
        ),
    )

    assert result.job_id == local_job_id
    assert len(repo.jobs) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_exam_converter_job_synchronizes_existing_terminal_status() -> None:
    actor = make_user()
    local_job_id = uuid4()
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[local_job_id] = ConversionHubJob(
        id=local_job_id,
        owner_user_id=actor.id,
        input_filename="prov.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-job-1",
        status=ConversionHubJobStatus.PROCESSING,
        correlation_id="corr-exam",
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    handler = RegisterExamConverterConversionHubJobHandler(
        jobs=repo,
        uow=FakeUow(),
        clock=SequenceClock(now + timedelta(seconds=30)),
        id_generator=SequenceIdGenerator([uuid4()]),
    )

    result = await handler.handle(
        actor=actor,
        request=RegisterExamConverterConversionHubJobRequest(
            correlation_id="corr-exam",
            input_filename="prov.dxe",
            status=ConversionHubJobStatus.SUCCEEDED,
            upstream_job_id="sir-job-1",
        ),
    )

    assert result.job_id == local_job_id
    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[local_job_id].status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[local_job_id].updated_at == now + timedelta(seconds=30)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_exam_converter_job_does_not_downgrade_existing_terminal_status() -> None:
    actor = make_user()
    local_job_id = uuid4()
    now = datetime(2026, 5, 19, tzinfo=timezone.utc)
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[local_job_id] = ConversionHubJob(
        id=local_job_id,
        owner_user_id=actor.id,
        input_filename="prov.dxe",
        source_format=ConversionHubSourceFormatV2.DIGIEXAM_DXE,
        output_format=ConversionHubOutputFormatV2.EXAMNET_BUNDLE,
        pdf_layout=None,
        upstream_job_id="sir-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-exam",
        error_message=None,
        created_at=now,
        updated_at=now,
    )
    handler = RegisterExamConverterConversionHubJobHandler(
        jobs=repo,
        uow=FakeUow(),
        clock=SequenceClock(now + timedelta(seconds=30)),
        id_generator=SequenceIdGenerator([uuid4()]),
    )

    result = await handler.handle(
        actor=actor,
        request=RegisterExamConverterConversionHubJobRequest(
            correlation_id="corr-exam",
            input_filename="prov.dxe",
            status=ConversionHubJobStatus.PROCESSING,
            upstream_job_id="sir-job-1",
        ),
    )

    assert result.job_id == local_job_id
    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[local_job_id].status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[local_job_id].updated_at == now


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_jobs_returns_local_ids_and_preserves_partial_batch_progress() -> None:
    actor = make_user()
    local_ids = [uuid4(), uuid4()]
    repo = InMemoryConversionHubJobRepository()
    client = FakeSirConvertClient()
    client.submit_results = [
        SirConvertSubmittedJobV2(
            job_id="up-1",
            status=SirConvertJobStatusV2.QUEUED,
            idempotent_replay=False,
        ),
        DomainError(code=ErrorCode.SERVICE_UNAVAILABLE, message="down"),
    ]
    handler = CreateConversionHubJobsHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator(local_ids.copy()),
    )

    result = await handler.handle(
        actor=actor,
        spec=_pdf_spec(),
        uploads=[
            ConversionHubUpload("one.html", "text/html", b"<h1>One</h1>"),
            ConversionHubUpload("two.html", "text/html", b"<h1>Two</h1>"),
        ],
        wait_seconds=0,
        correlation_id="corr-1",
        build_job_spec=_build_job_spec,
    )

    assert [job.job_id for job in result.jobs] == local_ids
    assert result.jobs[0].status is ConversionHubJobStatus.QUEUED
    assert result.jobs[0].error is None
    assert result.jobs[1].status is ConversionHubJobStatus.FAILED
    assert result.jobs[1].error == "Kunde inte starta konverteringen just nu. Försök igen."
    assert repo.jobs[local_ids[0]].upstream_job_id == "up-1"
    assert repo.jobs[local_ids[1]].upstream_job_id is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_jobs_rejects_invalid_spec_before_creating_local_job() -> None:
    actor = make_user()
    repo = InMemoryConversionHubJobRepository()
    client = FakeSirConvertClient()
    handler = CreateConversionHubJobsHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([uuid4()]),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(
            actor=actor,
            spec=ConversionHubJobSpecV2(
                source_format=ConversionHubSourceFormatV2.HTML,
                output_format=ConversionHubOutputFormatV2.MD,
                pdf_layout=_pdf_spec().pdf_layout,
            ),
            uploads=[ConversionHubUpload("one.html", "text/html", b"<h1>One</h1>")],
            wait_seconds=0,
            correlation_id="corr-invalid",
            build_job_spec=lambda **_: (_ for _ in ()).throw(
                DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="pdf_layout is only supported for PDF outputs.",
                )
            ),
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert repo.jobs == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_refreshes_owned_job_from_upstream() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename="classlist.pdf",
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=None,
        upstream_job_id="up-1",
        status=ConversionHubJobStatus.QUEUED,
        correlation_id="corr-1",
        error_message=None,
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["up-1"] = SirConvertJobV2(
        job_id="up-1",
        status=SirConvertJobStatusV2.SUCCEEDED,
    )
    handler = GetConversionHubJobHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, 0, 0, 1, tzinfo=timezone.utc)),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert result.job_id == job_id
    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[job_id].status is ConversionHubJobStatus.SUCCEEDED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_maps_running_upstream_status_to_processing() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename="classlist.pdf",
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=None,
        upstream_job_id="up-unknown",
        status=ConversionHubJobStatus.QUEUED,
        correlation_id="corr-unknown",
        error_message=None,
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["up-unknown"] = SirConvertJobV2(
        job_id="up-unknown",
        status=SirConvertJobStatusV2.RUNNING,
    )
    handler = GetConversionHubJobHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, 0, 0, 1, tzinfo=timezone.utc)),
    )

    result = await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-unknown")

    assert result.status is ConversionHubJobStatus.PROCESSING
    assert repo.jobs[job_id].status is ConversionHubJobStatus.PROCESSING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_rejects_unknown_upstream_status_fail_closed() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename="classlist.pdf",
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=None,
        upstream_job_id="up-mystery",
        status=ConversionHubJobStatus.QUEUED,
        correlation_id="corr-mystery",
        error_message=None,
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["up-mystery"] = DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message="Sir Convert-a-Lot v2 returned an unsupported job status.",
        details={
            "reason_code": "sir_convert_unknown_job_status",
            "status": "mystery",
        },
    )
    handler = GetConversionHubJobHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, 0, 0, 1, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id="corr-mystery")

    assert excinfo.value.code is ErrorCode.SERVICE_UNAVAILABLE
    assert repo.jobs[job_id].status is ConversionHubJobStatus.QUEUED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_artifact_proxies_owned_succeeded_job_after_refresh() -> None:
    actor = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = ConversionHubJob(
        id=job_id,
        owner_user_id=actor.id,
        input_filename="in.md",
        source_format=ConversionHubSourceFormatV2.MD,
        output_format=ConversionHubOutputFormatV2.PDF,
        pdf_layout=_pdf_spec().pdf_layout,
        upstream_job_id="up-2",
        status=ConversionHubJobStatus.PROCESSING,
        correlation_id="corr-2",
        error_message=None,
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    client = FakeSirConvertClient()
    client.jobs_by_upstream_id["up-2"] = SirConvertJobV2(
        job_id="up-2",
        status=SirConvertJobStatusV2.SUCCEEDED,
    )
    client.artifacts_by_upstream_id["up-2"] = SirConvertArtifactOutcomeV2(
        job_id="up-2",
        status="succeeded",
        artifact=SirConvertArtifactV2(
            filename="converted.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7",
        ),
    )
    handler = DownloadConversionHubArtifactHandler(
        jobs=repo,
        client=client,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, 0, 0, 1, tzinfo=timezone.utc)),
    )

    filename, content_type, content = await handler.handle(
        actor=actor,
        job_id=job_id,
        correlation_id="corr-2",
    )

    assert filename == "converted.pdf"
    assert content_type == "application/pdf"
    assert content == b"%PDF-1.7"
    assert repo.jobs[job_id].status is ConversionHubJobStatus.SUCCEEDED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_job_hides_foreign_job_as_not_found() -> None:
    actor = make_user()
    other_user = make_user()
    job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = ConversionHubJob(
        id=job_id,
        owner_user_id=other_user.id,
        input_filename="secret.pdf",
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        pdf_layout=None,
        upstream_job_id="up-3",
        status=ConversionHubJobStatus.QUEUED,
        correlation_id=None,
        error_message=None,
        created_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 27, tzinfo=timezone.utc),
    )
    handler = GetConversionHubJobHandler(
        jobs=repo,
        client=FakeSirConvertClient(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 3, 27, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, job_id=job_id, correlation_id=None)

    assert excinfo.value.code is ErrorCode.NOT_FOUND
