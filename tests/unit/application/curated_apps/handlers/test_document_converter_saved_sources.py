"""Behavioral tests for Document Converter saved-file source flows.

Purpose:
    Prove Document Converter can list and reuse owner-scoped compatible Vault
    files as server-side sources without downloading bytes through the browser.

Relationships:
    Exercises the saved-file source handlers that bridge Vault ownership and
    storage with the existing Document Converter job-creation path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
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
)
from skriptoteket.application.curated_apps.document_converter_producers import (
    DocumentConverterProducerPolicy,
    LocalDocumentConverterProducer,
)
from skriptoteket.application.curated_apps.handlers.document_converter_jobs import (
    CreateDocumentConverterJobsHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_saved_sources import (
    ListDocumentConverterSavedFilesHandler,
    SubmitDocumentConverterSavedFileHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.file_refs import build_vault_file_ref
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
)
from skriptoteket.protocols.documents import PdfTextExtractionProbe
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    FakeSirConvertClient,
    InMemoryConversionHubJobRepository,
    SequenceClock,
    SequenceIdGenerator,
)


class InMemoryVaultFileRepository:
    def __init__(self) -> None:
        self.files: dict[UUID, VaultFile] = {}

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        return self.files.get(file_id)

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]:
        del search, sort
        files = [file for file in self.files.values() if file.user_id == user_id]
        if state is VaultListState.ACTIVE:
            files = [file for file in files if file.deleted_at is None]
        else:
            files = [file for file in files if file.deleted_at is not None]
        return files[offset : offset + limit]

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        return [
            file
            for file in self.files.values()
            if file.user_id == user_id and file.deleted_at is None
        ]

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        files = [self.files[file_id] for file_id in file_ids if file_id in self.files]
        if include_deleted:
            return [file for file in files if file.user_id == user_id]
        return [file for file in files if file.user_id == user_id and file.deleted_at is None]

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        del cutoff, limit
        return []

    async def create(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def delete(self, *, file_id: UUID) -> None:
        self.files.pop(file_id, None)


class InMemoryVaultStorage:
    def __init__(self) -> None:
        self.files: dict[tuple[UUID, UUID], bytes] = {}

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        self.files[(user_id, file_id)] = content

    async def exists_file(self, *, user_id: UUID, file_id: UUID) -> bool:
        return (user_id, file_id) in self.files

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        return self.files[(user_id, file_id)]

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        self.files.pop((user_id, file_id), None)


class InMemoryDocumentConverterArtifactStore:
    def __init__(self) -> None:
        self.artifacts: dict[UUID, bytes] = {}

    def store_artifact(self, *, job_id: UUID, artifact) -> None:
        self.artifacts[job_id] = artifact.content

    def read_artifact(self, *, job_id: UUID):
        raise NotImplementedError


class StubPdfTextExtractor:
    def probe_text(self, *, file_bytes: bytes, filename: str) -> PdfTextExtractionProbe:
        del file_bytes, filename
        return PdfTextExtractionProbe(text="PDF text", heavy_reason=None)

    def extract_text(self, *, file_bytes: bytes, filename: str) -> str | None:
        del file_bytes, filename
        return "PDF text"


class StubHtmlToPdfRenderer:
    def render_html(self, *, html: str, base_url: str | Path | None = None) -> bytes:
        del base_url
        return f"pdf:{html}".encode("utf-8")


class StubMarkdownToHtmlRenderer:
    def render_markdown(self, *, markdown_text: str) -> str:
        return f"<p>{markdown_text}</p>"


def _vault_file(
    *,
    user_id: UUID,
    name: str,
    deleted_at: datetime | None = None,
) -> VaultFile:
    now = datetime(2026, 6, 26, tzinfo=timezone.utc)
    return VaultFile(
        id=uuid4(),
        user_id=user_id,
        name=name,
        bytes=128,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="document-converter:test",
        created_at=now,
        deleted_at=deleted_at,
    )


def _spec(*, source: ConversionHubSourceFormatV2, output: ConversionHubOutputFormatV2):
    return ConversionHubJobSpecV2(source_format=source, output_format=output)


def _build_job_spec(*, spec: ConversionHubJobSpecV2, filename: str) -> dict[str, object]:
    return {
        "source": {"filename": filename, "format": spec.source_format.value},
        "conversion": {"output_format": spec.output_format.value},
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_saved_files_only_returns_owned_supported_existing_files() -> None:
    actor = make_user()
    other_user = make_user()
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()

    compatible_html = _vault_file(user_id=actor.id, name="lektion.html")
    compatible_docx = _vault_file(user_id=actor.id, name="mall.docx")
    unsupported_txt = _vault_file(user_id=actor.id, name="anteckningar.txt")
    deleted_pdf = _vault_file(
        user_id=actor.id,
        name="arkiv.pdf",
        deleted_at=datetime(2026, 6, 26, 1, tzinfo=timezone.utc),
    )
    other_user_md = _vault_file(user_id=other_user.id, name="annans.md")
    missing_md = _vault_file(user_id=actor.id, name="saknas.md")

    for item in [
        compatible_html,
        compatible_docx,
        unsupported_txt,
        deleted_pdf,
        other_user_md,
        missing_md,
    ]:
        vault_files.files[item.id] = item

    await vault_storage.store_file(
        user_id=actor.id,
        file_id=compatible_html.id,
        content=b"<h1>Hej</h1>",
    )
    await vault_storage.store_file(
        user_id=actor.id,
        file_id=compatible_docx.id,
        content=b"docx",
    )

    handler = ListDocumentConverterSavedFilesHandler(
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=FakeUow(),
    )

    result = await handler.handle(actor=actor)

    assert [(item.name, item.source_format) for item in result.files] == [
        ("lektion.html", ConversionHubSourceFormatV2.HTML),
        (
            "mall.docx",
            ConversionHubSourceFormatV2.DOCX,
        ),
    ]
    assert all(item.ref == build_vault_file_ref(file_id=item.file_id) for item in result.files)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_saved_file_reads_vault_bytes_and_reuses_document_converter_job_creation() -> (
    None
):
    actor = make_user()
    vault_file = _vault_file(user_id=actor.id, name="lektion.html")
    vault_files = InMemoryVaultFileRepository()
    vault_files.files[vault_file.id] = vault_file
    vault_storage = InMemoryVaultStorage()
    await vault_storage.store_file(
        user_id=actor.id,
        file_id=vault_file.id,
        content=b"<h1>Hej</h1>",
    )

    jobs = InMemoryConversionHubJobRepository()
    local_artifacts = InMemoryDocumentConverterArtifactStore()
    create_handler = CreateDocumentConverterJobsHandler(
        jobs=jobs,
        client=FakeSirConvertClient(),
        policy=DocumentConverterProducerPolicy(pdf_text_extractor=StubPdfTextExtractor()),
        local_producer=LocalDocumentConverterProducer(
            html_to_pdf=StubHtmlToPdfRenderer(),
            markdown_to_html=StubMarkdownToHtmlRenderer(),
            pdf_text_extractor=StubPdfTextExtractor(),
        ),
        local_artifacts=local_artifacts,
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 26, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([uuid4()]),
    )
    submit_handler = SubmitDocumentConverterSavedFileHandler(
        create_jobs=create_handler,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=FakeUow(),
    )

    result = await submit_handler.handle(
        actor=actor,
        spec=_spec(
            source=ConversionHubSourceFormatV2.HTML,
            output=ConversionHubOutputFormatV2.PDF,
        ),
        source_ref=build_vault_file_ref(file_id=vault_file.id),
        wait_seconds=0,
        correlation_id="corr-1",
        build_job_spec=_build_job_spec,
    )

    assert len(result.jobs) == 1
    assert result.jobs[0].input_filename == "lektion.html"
    assert result.jobs[0].status is ConversionHubJobStatus.SUCCEEDED
    assert result.jobs[0].producer is DocumentConverterProducerKind.LOCAL
    assert next(iter(local_artifacts.artifacts.values())) == b"pdf:<h1>Hej</h1>"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_saved_file_rejects_cross_owner_deleted_and_unsupported_refs() -> None:
    actor = make_user()
    other_user = make_user()
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()

    other_owner_file = _vault_file(user_id=other_user.id, name="annans.html")
    deleted_file = _vault_file(
        user_id=actor.id,
        name="borttagen.pdf",
        deleted_at=datetime(2026, 6, 26, tzinfo=timezone.utc),
    )
    unsupported_file = _vault_file(user_id=actor.id, name="notes.txt")
    for item in [other_owner_file, deleted_file, unsupported_file]:
        vault_files.files[item.id] = item

    await vault_storage.store_file(
        user_id=actor.id,
        file_id=unsupported_file.id,
        content=b"text",
    )

    create_handler = CreateDocumentConverterJobsHandler(
        jobs=InMemoryConversionHubJobRepository(),
        client=FakeSirConvertClient(),
        policy=DocumentConverterProducerPolicy(pdf_text_extractor=StubPdfTextExtractor()),
        local_producer=LocalDocumentConverterProducer(
            html_to_pdf=StubHtmlToPdfRenderer(),
            markdown_to_html=StubMarkdownToHtmlRenderer(),
            pdf_text_extractor=StubPdfTextExtractor(),
        ),
        local_artifacts=InMemoryDocumentConverterArtifactStore(),
        uow=FakeUow(),
        clock=SequenceClock(datetime(2026, 6, 26, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([uuid4()]),
    )
    handler = SubmitDocumentConverterSavedFileHandler(
        create_jobs=create_handler,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=FakeUow(),
    )

    with pytest.raises(DomainError) as cross_owner_exc:
        await handler.handle(
            actor=actor,
            spec=_spec(
                source=ConversionHubSourceFormatV2.HTML,
                output=ConversionHubOutputFormatV2.PDF,
            ),
            source_ref=build_vault_file_ref(file_id=other_owner_file.id),
            wait_seconds=0,
            correlation_id=None,
            build_job_spec=_build_job_spec,
        )
    assert cross_owner_exc.value.code is ErrorCode.NOT_FOUND

    with pytest.raises(DomainError) as deleted_exc:
        await handler.handle(
            actor=actor,
            spec=_spec(
                source=ConversionHubSourceFormatV2.PDF,
                output=ConversionHubOutputFormatV2.MD,
            ),
            source_ref=build_vault_file_ref(file_id=deleted_file.id),
            wait_seconds=0,
            correlation_id=None,
            build_job_spec=_build_job_spec,
        )
    assert deleted_exc.value.code is ErrorCode.NOT_FOUND

    with pytest.raises(DomainError) as unsupported_exc:
        await handler.handle(
            actor=actor,
            spec=_spec(
                source=ConversionHubSourceFormatV2.MD,
                output=ConversionHubOutputFormatV2.PDF,
            ),
            source_ref=build_vault_file_ref(file_id=unsupported_file.id),
            wait_seconds=0,
            correlation_id=None,
            build_job_spec=_build_job_spec,
        )
    assert unsupported_exc.value.code is ErrorCode.VALIDATION_ERROR
