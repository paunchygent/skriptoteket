"""Document Converter save/export filename adoption tests.

Purpose:
    Prove Document Converter applies the ST-37-05 filename protocol for
    single-file and HTML/CSS project-preview outputs through backend-owned
    status, download, and Mina filer save authority.

Relationships:
    Exercises application handlers over protocol fakes so frontend code can
    consume returned filename metadata without owning final extension,
    content-type, or duplicate-save disambiguation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobStatus,
    ConversionHubOutputFormatV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
    build_document_converter_result_artifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_document_converter import (
    DownloadDocumentConverterArtifactHandler,
    SaveDocumentConverterArtifactHandler,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    RenderDocumentConverterProjectPreviewHandler,
    SaveDocumentConverterProjectPreviewArtifactHandler,
)
from skriptoteket.domain.scripting.vault import VaultFileSourceKind, VaultUsage
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import (
    FixedClock,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    FakeSirConvertClient,
    InMemoryConversionHubJobRepository,
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryDocumentConverterArtifactStore,
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
    _artifact,
    _settings,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_project_previews import (
    InMemoryProjectPreviewStore,
)

NOW = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)


def _job(
    *,
    job_id: UUID,
    owner_user_id: UUID,
    input_filename: str,
    output_format: ConversionHubOutputFormatV2,
) -> ConversionHubJob:
    return ConversionHubJob(
        id=job_id,
        owner_user_id=owner_user_id,
        input_filename=input_filename,
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=output_format,
        pdf_layout=None,
        upstream_job_id="sir-job-1",
        status=ConversionHubJobStatus.SUCCEEDED,
        correlation_id="corr-1",
        error_message=None,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("output_format", "expected_filename"),
    [
        (ConversionHubOutputFormatV2.PDF, "Lektionsplanering - Konverterad PDF - 20260627.pdf"),
        (ConversionHubOutputFormatV2.DOCX, "Lektionsplanering - Word-dokument - 20260627.docx"),
        (ConversionHubOutputFormatV2.MD, "Lektionsplanering - Markdown - 20260627.md"),
    ],
)
def test_single_file_result_metadata_uses_protocol_filename(
    output_format: ConversionHubOutputFormatV2,
    expected_filename: str,
) -> None:
    actor = make_user()

    artifact = build_document_converter_result_artifact(
        job=_job(
            job_id=uuid4(),
            owner_user_id=actor.id,
            input_filename="Lektionsplanering.html",
            output_format=output_format,
        )
    )

    assert artifact is not None
    assert artifact.filename == expected_filename


@pytest.mark.unit
@pytest.mark.asyncio
async def test_single_file_download_and_repeated_saves_use_backend_final_filenames() -> None:
    actor = make_user()
    job_id = uuid4()
    first_file_id = uuid4()
    second_file_id = uuid4()
    repo = InMemoryConversionHubJobRepository()
    repo.jobs[job_id] = _job(
        job_id=job_id,
        owner_user_id=actor.id,
        input_filename="Lektionsplanering.html",
        output_format=ConversionHubOutputFormatV2.PDF,
    )
    client = FakeSirConvertClient()
    client.artifacts_by_upstream_id["sir-job-1"] = _artifact(content=b"%PDF-1.7\n")
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()
    vault_usage = InMemoryVaultUsageRepository(
        usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=NOW)
    )
    local_artifacts = InMemoryDocumentConverterArtifactStore()
    uow = FakeUow()
    clock = FixedClock(NOW)
    download = DownloadDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=local_artifacts,
        uow=uow,
        clock=clock,
    )
    save = SaveDocumentConverterArtifactHandler(
        jobs=repo,
        client=client,
        local_artifacts=local_artifacts,
        vault_files=vault_files,
        vault_usage=vault_usage,
        vault_storage=vault_storage,
        uow=uow,
        clock=clock,
        id_generator=SequenceIdGenerator([first_file_id, second_file_id]),
        settings=_settings(),
    )

    filename, content_type, content = await download.handle(
        actor=actor,
        job_id=job_id,
        correlation_id="corr-1",
    )
    first = await save.handle(actor=actor, job_id=job_id, correlation_id="corr-1")
    second = await save.handle(actor=actor, job_id=job_id, correlation_id="corr-1")

    assert filename == "Lektionsplanering - Konverterad PDF - 20260627.pdf"
    assert content_type == "application/pdf"
    assert content == b"%PDF-1.7\n"
    assert first.vault_artifact.name == "Lektionsplanering - Konverterad PDF - 20260627.pdf"
    assert second.vault_artifact.name == ("Lektionsplanering - Konverterad PDF - 20260627 (2).pdf")
    assert vault_files.files[first_file_id].source_artifact_id == (
        "document-converter:sir-job-1:converted_document"
    )
    assert vault_files.files[second_file_id].source_kind is VaultFileSourceKind.APP_EXPORT


def _manifest() -> DocumentConverterProjectManifest:
    return DocumentConverterProjectManifest.model_validate(
        {
            "html_entries": [
                {
                    "entry_id": "raw-entry-one",
                    "filename": "lektion.html",
                    "title": "Svenska lektion",
                },
                {
                    "entry_id": "raw-entry-two",
                    "filename": "appendix.html",
                    "title": "Bilaga",
                },
            ],
            "css_files": [],
            "image_files": [],
            "font_files": [],
            "output_mode": "both",
            "pdf_controls": {
                "paper_size": "a4",
                "orientation": "portrait",
                "margins": {
                    "top_mm": 12,
                    "right_mm": 12,
                    "bottom_mm": 12,
                    "left_mm": 12,
                },
                "template_id": "academic_phd",
            },
        }
    )


def _uploads() -> list[DocumentConverterProjectUploadedFile]:
    return [
        DocumentConverterProjectUploadedFile(
            filename="lektion.html",
            content_type="text/html",
            content=b"<h1>Svenska</h1>",
        ),
        DocumentConverterProjectUploadedFile(
            filename="appendix.html",
            content_type="text/html",
            content=b"<h1>Bilaga</h1>",
        ),
    ]


class NamingProjectRenderer:
    def render_project(
        self,
        *,
        manifest: DocumentConverterProjectManifest,
        files: list[DocumentConverterProjectUploadedFile],
    ) -> list[DocumentConverterStoredArtifact]:
        del files
        artifacts = [
            DocumentConverterStoredArtifact(
                filename=f"{entry.entry_id}.pdf",
                content_type="application/pdf",
                content=f"%PDF-{entry.entry_id}".encode(),
            )
            for entry in manifest.html_entries
        ]
        if manifest.output_mode in {
            DocumentConverterProjectOutputMode.COMBINED_PDF,
            DocumentConverterProjectOutputMode.BOTH,
        }:
            artifacts.append(
                DocumentConverterStoredArtifact(
                    filename="combined.pdf",
                    content_type="application/pdf",
                    content=b"%PDF-COMBINED",
                )
            )
        return artifacts


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_preview_names_separate_and_combined_outputs_without_raw_ids() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_ids = [uuid4(), uuid4(), uuid4()]
    store = InMemoryProjectPreviewStore()
    handler = RenderDocumentConverterProjectPreviewHandler(
        renderer=NamingProjectRenderer(),
        previews=store,
        clock=FixedClock(NOW),
        id_generator=SequenceIdGenerator([preview_id, *artifact_ids]),
    )

    result = await handler.handle(actor=actor, manifest=_manifest(), files=_uploads())

    assert [artifact.filename for artifact in result.artifacts] == [
        "Svenska lektion - Separat PDF - 20260627.pdf",
        "Bilaga - Separat PDF - 20260627.pdf",
        "Svenska lektion - Sammanslagen PDF - 20260627.pdf",
    ]
    assert all("raw-entry" not in artifact.filename for artifact in result.artifacts)
    assert all(str(artifact.artifact_id) not in artifact.filename for artifact in result.artifacts)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_preview_save_uses_protocol_name_and_disambiguates_repeat_saves() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_ids = [uuid4(), uuid4(), uuid4()]
    first_file_id = uuid4()
    second_file_id = uuid4()
    store = InMemoryProjectPreviewStore()
    render = RenderDocumentConverterProjectPreviewHandler(
        renderer=NamingProjectRenderer(),
        previews=store,
        clock=FixedClock(NOW),
        id_generator=SequenceIdGenerator([preview_id, *artifact_ids]),
    )
    result = await render.handle(actor=actor, manifest=_manifest(), files=_uploads())
    combined_artifact_id = result.artifacts[-1].artifact_id
    vault_files = InMemoryVaultFileRepository()
    save = SaveDocumentConverterProjectPreviewArtifactHandler(
        previews=store,
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(user_id=actor.id, bytes_total=0, updated_at=NOW)
        ),
        vault_storage=InMemoryVaultStorage(),
        uow=FakeUow(),
        clock=FixedClock(NOW),
        id_generator=SequenceIdGenerator([first_file_id, second_file_id]),
        settings=_settings(),
    )

    first = await save.handle(
        actor=actor,
        preview_id=preview_id,
        artifact_id=combined_artifact_id,
    )
    second = await save.handle(
        actor=actor,
        preview_id=preview_id,
        artifact_id=combined_artifact_id,
    )

    assert first.vault_artifact.name == "Svenska lektion - Sammanslagen PDF - 20260627.pdf"
    assert second.vault_artifact.name == ("Svenska lektion - Sammanslagen PDF - 20260627 (2).pdf")
    assert vault_files.files[first_file_id].source_artifact_id == (
        f"document-converter:project-preview:{preview_id}:{combined_artifact_id}"
    )
