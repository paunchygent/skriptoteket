"""Document Converter producer-policy tests.

Purpose:
    Prove local CPU selection, unavailable-route rejection, and owner-scoped jobs.

Relationships:
    Exercises the application handler and routing policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterProducerKind,
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_producers import (
    DocumentConverterProducerPolicy,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    ConversionHubUpload,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.documents import PdfTextExtractionProbe
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactOutcomeV2,
    SirConvertJobV2,
    SirConvertSubmitRequestV2,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    InMemoryConversionHubJobRepository,
    SequenceClock,
    SequenceIdGenerator,
)


class FakePdfTextExtractor:
    def __init__(
        self,
        text_by_filename: dict[str, str | None] | None = None,
        probe_by_filename: dict[str, PdfTextExtractionProbe] | None = None,
    ) -> None:
        self.text_by_filename = text_by_filename or {}
        self.probe_by_filename = probe_by_filename or {}
        self.calls: list[str] = []

    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None:
        del file_bytes
        self.calls.append(filename)
        return self.text_by_filename.get(filename)

    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe:
        del file_bytes
        self.calls.append(filename)
        return self.probe_by_filename.get(
            filename,
            PdfTextExtractionProbe(text=self.text_by_filename.get(filename)),
        )


class FakeLocalProducer:
    def __init__(self, artifact: DocumentConverterStoredArtifact) -> None:
        self.artifact = artifact
        self.calls: list[ConversionHubUpload] = []

    async def convert(
        self,
        *,
        spec: ConversionHubJobSpecV2,
        upload: ConversionHubUpload,
        correlation_id: str | None,
    ) -> DocumentConverterStoredArtifact:
        del spec, correlation_id
        self.calls.append(upload)
        return self.artifact


class InMemoryDocumentConverterArtifactStore:
    def __init__(self) -> None:
        self.artifacts: dict[UUID, DocumentConverterStoredArtifact] = {}

    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: DocumentConverterStoredArtifact,
    ) -> None:
        self.artifacts[job_id] = artifact

    def read_artifact(self, *, job_id: UUID) -> DocumentConverterStoredArtifact:
        return self.artifacts[job_id]


class FailingDocumentConverterArtifactStore(InMemoryDocumentConverterArtifactStore):
    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: DocumentConverterStoredArtifact,
    ) -> None:
        del job_id, artifact
        raise OSError("disk full")


class RecordingSirConvertClient:
    def __init__(self) -> None:
        self.submit_results: list[SirConvertSubmittedJobV2] = []
        self.submitted_requests: list[SirConvertSubmitRequestV2] = []

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
        self.submitted_requests.append(request)
        return self.submit_results.pop(0)

    async def get_job(self, job_id: str, *, correlation_id: str | None) -> SirConvertJobV2:
        del job_id, correlation_id
        raise NotImplementedError

    async def download_artifact(
        self,
        job_id: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2:
        del job_id, correlation_id
        raise NotImplementedError

    async def download_named_artifact(
        self,
        job_id: str,
        artifact_key: str,
        *,
        correlation_id: str | None,
    ) -> SirConvertArtifactOutcomeV2:
        del job_id, artifact_key, correlation_id
        raise NotImplementedError

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


def _html_pdf_spec() -> ConversionHubJobSpecV2:
    return ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
    )


def _pdf_markdown_spec() -> ConversionHubJobSpecV2:
    return ConversionHubJobSpecV2(
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
    )


def _build_job_spec(*, spec: ConversionHubJobSpecV2, filename: str) -> dict[str, object]:
    return {
        "source": {"filename": filename, "format": spec.source_format.value},
        "conversion": {"output_format": spec.output_format.value},
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_converter_policy_marks_simple_html_pdf_as_local() -> None:
    policy = DocumentConverterProducerPolicy(pdf_text_extractor=FakePdfTextExtractor())

    decision = await policy.decide(
        spec=_html_pdf_spec(),
        upload=ConversionHubUpload("source.html", "text/html", b"<h1>Hej</h1>"),
        correlation_id="corr-1",
    )

    assert decision.producer is DocumentConverterProducerKind.LOCAL
    assert decision.reason == "local_html_to_pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_converter_policy_rejects_pdf_without_text() -> None:
    extractor = FakePdfTextExtractor({"scan.pdf": None})
    policy = DocumentConverterProducerPolicy(pdf_text_extractor=extractor)

    with pytest.raises(DomainError) as excinfo:
        await policy.decide(
            spec=_pdf_markdown_spec(),
            upload=ConversionHubUpload("scan.pdf", "application/pdf", b"%PDF-1.7"),
            correlation_id="corr-1",
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert excinfo.value.message == "PDF-filen saknar ett läsbart textlager."
    assert extractor.calls == ["scan.pdf"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_converter_policy_keeps_simple_extractable_pdf_local() -> None:
    extractor = FakePdfTextExtractor(
        text_by_filename={"simple.pdf": "Plain paragraph text for a worksheet."},
        probe_by_filename={
            "simple.pdf": PdfTextExtractionProbe(text="Plain paragraph text for a worksheet.")
        },
    )
    policy = DocumentConverterProducerPolicy(pdf_text_extractor=extractor)

    decision = await policy.decide(
        spec=_pdf_markdown_spec(),
        upload=ConversionHubUpload("simple.pdf", "application/pdf", b"%PDF-1.7"),
        correlation_id="corr-1",
    )

    assert decision.producer is DocumentConverterProducerKind.LOCAL
    assert decision.reason == "local_pdf_text_to_markdown"
    assert extractor.calls == ["simple.pdf"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_document_converter_policy_rejects_pdf_that_requires_ocr() -> None:
    extractor = FakePdfTextExtractor(
        text_by_filename={"table.pdf": "Column A Column B\n1 2\n3 4"},
        probe_by_filename={
            "table.pdf": PdfTextExtractionProbe(
                text="Column A Column B\n1 2\n3 4",
                heavy_reason="table_dense_pdf",
            )
        },
    )
    policy = DocumentConverterProducerPolicy(pdf_text_extractor=extractor)

    with pytest.raises(DomainError) as excinfo:
        await policy.decide(
            spec=_pdf_markdown_spec(),
            upload=ConversionHubUpload("table.pdf", "application/pdf", b"%PDF-1.7"),
            correlation_id="corr-1",
        )

    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert excinfo.value.message == (
        "PDF-filen kräver textigenkänning som inte är tillgänglig för närvarande."
    )
    assert extractor.calls == ["table.pdf"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_document_converter_jobs_stores_local_artifact_without_sir_submission() -> (
    None
):
    actor = make_user()
    local_job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    client = RecordingSirConvertClient()
    store = InMemoryDocumentConverterArtifactStore()
    producer = FakeLocalProducer(
        DocumentConverterStoredArtifact(
            filename="source.pdf",
            content_type="application/pdf",
            content=b"%PDF-LOCAL",
        )
    )
    handler = CreateDocumentConverterJobsHandler(
        jobs=repo,
        client=client,
        policy=DocumentConverterProducerPolicy(pdf_text_extractor=FakePdfTextExtractor()),
        local_producer=producer,
        local_artifacts=store,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([local_job_id]),
    )

    result = await handler.handle(
        actor=actor,
        spec=_html_pdf_spec(),
        uploads=[ConversionHubUpload("source.html", "text/html", b"<h1>Hej</h1>")],
        wait_seconds=0,
        correlation_id="corr-1",
        build_job_spec=_build_job_spec,
    )

    assert result.jobs[0].producer is DocumentConverterProducerKind.LOCAL
    assert result.jobs[0].producer_reason == "local_html_to_pdf"
    assert repo.jobs[local_job_id].status is ConversionHubJobStatus.SUCCEEDED
    assert repo.jobs[local_job_id].upstream_job_id == f"local:{local_job_id}"
    assert store.artifacts[local_job_id].content == b"%PDF-LOCAL"
    assert [upload.filename for upload in producer.calls] == ["source.html"]
    assert client.submitted_requests == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_document_converter_jobs_marks_failed_when_local_artifact_store_fails() -> (
    None
):
    actor = make_user()
    local_job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    client = RecordingSirConvertClient()
    producer = FakeLocalProducer(
        DocumentConverterStoredArtifact(
            filename="source.pdf",
            content_type="application/pdf",
            content=b"%PDF-LOCAL",
        )
    )
    handler = CreateDocumentConverterJobsHandler(
        jobs=repo,
        client=client,
        policy=DocumentConverterProducerPolicy(pdf_text_extractor=FakePdfTextExtractor()),
        local_producer=producer,
        local_artifacts=FailingDocumentConverterArtifactStore(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([local_job_id]),
    )

    result = await handler.handle(
        actor=actor,
        spec=_html_pdf_spec(),
        uploads=[ConversionHubUpload("source.html", "text/html", b"<h1>Hej</h1>")],
        wait_seconds=0,
        correlation_id="corr-1",
        build_job_spec=_build_job_spec,
    )

    assert result.jobs[0].producer is DocumentConverterProducerKind.LOCAL
    assert result.jobs[0].status is ConversionHubJobStatus.FAILED
    assert result.jobs[0].error == "Kunde inte spara konverteringsresultatet just nu."
    assert repo.jobs[local_job_id].status is ConversionHubJobStatus.FAILED
    assert repo.jobs[local_job_id].upstream_job_id is None
    assert repo.jobs[local_job_id].error_message == result.jobs[0].error
    assert [upload.filename for upload in producer.calls] == ["source.html"]
    assert client.submitted_requests == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_document_converter_jobs_rejects_pdf_without_text_before_job_creation() -> (
    None
):
    actor = make_user()
    local_job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    client = RecordingSirConvertClient()
    store = InMemoryDocumentConverterArtifactStore()
    producer = FakeLocalProducer(
        DocumentConverterStoredArtifact(
            filename="scan.md",
            content_type="text/markdown; charset=utf-8",
            content=b"local",
        )
    )
    handler = CreateDocumentConverterJobsHandler(
        jobs=repo,
        client=client,
        policy=DocumentConverterProducerPolicy(
            pdf_text_extractor=FakePdfTextExtractor({"scan.pdf": None})
        ),
        local_producer=producer,
        local_artifacts=store,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([local_job_id]),
    )

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            spec=_pdf_markdown_spec(),
            uploads=[ConversionHubUpload("scan.pdf", "application/pdf", b"%PDF-1.7")],
            wait_seconds=0,
            correlation_id="corr-1",
            build_job_spec=_build_job_spec,
        )

    assert repo.jobs == {}
    assert client.submitted_requests == []
    assert store.artifacts == {}
    assert producer.calls == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_document_converter_jobs_rejects_complex_pdf_before_job_creation() -> None:
    actor = make_user()
    local_job_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    client = RecordingSirConvertClient()
    store = InMemoryDocumentConverterArtifactStore()
    producer = FakeLocalProducer(
        DocumentConverterStoredArtifact(
            filename="table.md",
            content_type="text/markdown; charset=utf-8",
            content=b"degraded local markdown",
        )
    )
    handler = CreateDocumentConverterJobsHandler(
        jobs=repo,
        client=client,
        policy=DocumentConverterProducerPolicy(
            pdf_text_extractor=FakePdfTextExtractor(
                text_by_filename={"table.pdf": "Column A Column B\n1 2\n3 4"},
                probe_by_filename={
                    "table.pdf": PdfTextExtractionProbe(
                        text="Column A Column B\n1 2\n3 4",
                        heavy_reason="table_dense_pdf",
                    )
                },
            )
        ),
        local_producer=producer,
        local_artifacts=store,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([local_job_id]),
    )

    with pytest.raises(DomainError):
        await handler.handle(
            actor=actor,
            spec=_pdf_markdown_spec(),
            uploads=[ConversionHubUpload("table.pdf", "application/pdf", b"%PDF-1.7")],
            wait_seconds=0,
            correlation_id="corr-1",
            build_job_spec=_build_job_spec,
        )

    assert repo.jobs == {}
    assert client.submitted_requests == []
    assert store.artifacts == {}
    assert producer.calls == []
