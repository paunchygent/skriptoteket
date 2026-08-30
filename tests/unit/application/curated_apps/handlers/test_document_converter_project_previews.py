"""Document Converter project preview handler tests.

Purpose:
    Prove HTML/CSS project preview rendering creates owner-scoped temporary
    server artifacts that can be inspected, discarded, and explicitly saved.

Relationships:
    Exercises project preview handlers over protocol fakes. Filesystem renderer
    sandbox behavior is covered by infrastructure document preview tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DOCUMENT_CONVERTER_PROJECT_PREVIEW_TTL_SECONDS,
    CleanupDocumentConverterProjectPreviewsResult,
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectPreviewStatus,
    DocumentConverterProjectUploadedFile,
    build_document_converter_project_preview_source_artifact_id,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    CleanupDocumentConverterProjectPreviewsHandler,
    DiscardDocumentConverterProjectPreviewHandler,
    DownloadDocumentConverterProjectPreviewArtifactHandler,
    GetDocumentConverterProjectPreviewHandler,
    RenderDocumentConverterProjectPreviewHandler,
    SaveDocumentConverterProjectPreviewArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.vault import VaultFileSourceKind, VaultUsage
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.identity_fixtures import make_user
from tests.fixtures.time_fixtures import (
    FixedClock,
)
from tests.unit.application.curated_apps.handlers.test_conversion_hub_jobs import (
    SequenceIdGenerator,
)
from tests.unit.application.curated_apps.handlers.test_document_converter_artifact_saves import (
    InMemoryVaultFileRepository,
    InMemoryVaultStorage,
    InMemoryVaultUsageRepository,
)


class RecordingProjectRenderer:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def render_project(
        self,
        *,
        manifest: DocumentConverterProjectManifest,
        files: list[DocumentConverterProjectUploadedFile],
    ) -> list[DocumentConverterStoredArtifact]:
        self.calls.append({"manifest": manifest, "files": files})
        artifacts: list[DocumentConverterStoredArtifact] = []
        if manifest.output_mode in {
            DocumentConverterProjectOutputMode.SEPARATE_PDFS,
            DocumentConverterProjectOutputMode.BOTH,
        }:
            artifacts.extend(
                DocumentConverterStoredArtifact(
                    filename=f"{entry.entry_id}.pdf",
                    content_type="application/pdf",
                    content=f"%PDF-{entry.entry_id}".encode("utf-8"),
                )
                for entry in manifest.html_entries
            )
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


def _manifest(*, output_mode: str = "both") -> DocumentConverterProjectManifest:
    return DocumentConverterProjectManifest.model_validate(
        {
            "html_entries": [
                {"entry_id": "one", "filename": "one.html"},
                {"entry_id": "two", "filename": "two.html"},
            ],
            "css_files": ["style.css"],
            "image_files": ["logo.png"],
            "font_files": [],
            "output_mode": output_mode,
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
            filename="one.html",
            content_type="text/html",
            content=b"<h1>One</h1>",
        ),
        DocumentConverterProjectUploadedFile(
            filename="two.html",
            content_type="text/html",
            content=b"<h1>Two</h1>",
        ),
        DocumentConverterProjectUploadedFile(
            filename="style.css",
            content_type="text/css",
            content=b"h1 { color: #222; }",
        ),
        DocumentConverterProjectUploadedFile(
            filename="logo.png",
            content_type="image/png",
            content=b"png",
        ),
    ]


def _settings() -> Settings:
    return Settings.model_construct(
        VAULT_MAX_FILE_BYTES=1_000_000,
        VAULT_MAX_TOTAL_BYTES=2_000_000,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_render_project_preview_stores_server_owned_artifacts_with_24h_ttl() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_ids = [uuid4(), uuid4(), uuid4()]
    now = datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc)
    store = InMemoryProjectPreviewStore()
    renderer = RecordingProjectRenderer()
    handler = RenderDocumentConverterProjectPreviewHandler(
        renderer=renderer,
        previews=store,
        clock=FixedClock(now),
        id_generator=SequenceIdGenerator([preview_id, *artifact_ids]),
    )

    result = await handler.handle(actor=actor, manifest=_manifest(), files=_uploads())

    assert result.preview_id == preview_id
    assert result.status is DocumentConverterProjectPreviewStatus.SUCCEEDED
    assert result.expires_at == now + timedelta(
        seconds=DOCUMENT_CONVERTER_PROJECT_PREVIEW_TTL_SECONDS
    )
    assert [artifact.artifact_id for artifact in result.artifacts] == artifact_ids
    assert {artifact.filename for artifact in result.artifacts} == {
        "one - Separat PDF - 20260625.pdf",
        "two - Separat PDF - 20260625.pdf",
        "one - Sammanslagen PDF - 20260625.pdf",
    }
    assert all(artifact.download_url is None for artifact in result.artifacts)
    assert store.records[(actor.id, preview_id)].owner_user_id == actor.id
    assert renderer.calls[0]["manifest"] == _manifest()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_project_preview_status_hides_foreign_and_discarded_previews() -> None:
    actor = make_user()
    other = make_user()
    preview_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(actor=other, preview_id=preview_id, store=store)
    handler = GetDocumentConverterProjectPreviewHandler(
        previews=store,
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )

    with pytest.raises(DomainError) as excinfo:
        await handler.handle(actor=actor, preview_id=preview_id)

    assert excinfo.value.code is ErrorCode.NOT_FOUND


@pytest.mark.unit
@pytest.mark.asyncio
async def test_discard_project_preview_removes_download_authority() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(actor=actor, preview_id=preview_id, artifact_id=artifact_id, store=store)
    discard = DiscardDocumentConverterProjectPreviewHandler(
        previews=store,
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )
    download = DownloadDocumentConverterProjectPreviewArtifactHandler(
        previews=store,
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
    )

    result = await discard.handle(actor=actor, preview_id=preview_id)

    assert result.status is DocumentConverterProjectPreviewStatus.DISCARDED
    with pytest.raises(DomainError) as excinfo:
        await download.handle(actor=actor, preview_id=preview_id, artifact_id=artifact_id)
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_project_preview_artifact_uses_preview_and_artifact_id_authority() -> None:
    actor = make_user()
    preview_id = uuid4()
    artifact_id = uuid4()
    file_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(actor=actor, preview_id=preview_id, artifact_id=artifact_id, store=store)
    vault_files = InMemoryVaultFileRepository()
    vault_storage = InMemoryVaultStorage()
    handler = SaveDocumentConverterProjectPreviewArtifactHandler(
        previews=store,
        vault_files=vault_files,
        vault_usage=InMemoryVaultUsageRepository(
            usage=VaultUsage(
                user_id=actor.id,
                bytes_total=0,
                updated_at=datetime(2026, 6, 25, tzinfo=timezone.utc),
            )
        ),
        vault_storage=vault_storage,
        uow=FakeUow(),
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([file_id]),
        settings=_settings(),
    )

    result = await handler.handle(actor=actor, preview_id=preview_id, artifact_id=artifact_id)

    expected_source = build_document_converter_project_preview_source_artifact_id(
        preview_id=preview_id,
        artifact_id=artifact_id,
    )
    saved_file = vault_files.files[file_id]
    assert saved_file.source_kind is VaultFileSourceKind.APP_EXPORT
    assert saved_file.source_artifact_id == expected_source
    assert vault_storage.stored[(actor.id, file_id)] == b"%PDF-COMBINED"
    assert result.source_artifact_id == expected_source
    assert isinstance(result.vault_artifact, ConversionHubSavedVaultArtifact)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cleanup_project_previews_removes_expired_artifacts_only() -> None:
    actor = make_user()
    now = datetime(2026, 6, 25, 8, 0, tzinfo=timezone.utc)
    expired_preview_id = uuid4()
    active_preview_id = uuid4()
    store = InMemoryProjectPreviewStore()
    await _store_preview(
        actor=actor,
        preview_id=expired_preview_id,
        store=store,
        expires_at=now - timedelta(seconds=1),
    )
    await _store_preview(
        actor=actor,
        preview_id=active_preview_id,
        store=store,
        expires_at=now + timedelta(hours=1),
    )
    handler = CleanupDocumentConverterProjectPreviewsHandler(
        previews=store,
        clock=FixedClock(now),
    )

    result = await handler.handle()

    assert result.deleted_previews == 1
    assert (actor.id, expired_preview_id) not in store.records
    assert (actor.id, active_preview_id) in store.records


class InMemoryProjectPreviewStore:
    def __init__(self) -> None:
        self.records: dict[tuple[UUID, UUID], DocumentConverterProjectPreviewRecord] = {}
        self.artifacts: dict[tuple[UUID, UUID, UUID], DocumentConverterStoredArtifact] = {}

    def store_preview(
        self,
        *,
        record: DocumentConverterProjectPreviewRecord,
        artifacts: list[DocumentConverterStoredArtifact],
    ) -> None:
        self.records[(record.owner_user_id, record.preview_id)] = record
        for artifact_meta, artifact in zip(record.artifacts, artifacts, strict=True):
            self.artifacts[(record.owner_user_id, record.preview_id, artifact_meta.artifact_id)] = (
                artifact
            )

    def get_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord:
        record = self.records.get((owner_user_id, preview_id))
        if record is None:
            raise DomainError(
                code=ErrorCode.NOT_FOUND,
                message=f"DocumentConverterProjectPreview not found: {preview_id}",
            )
        if record.expires_at <= now:
            return record.model_copy(
                update={"status": DocumentConverterProjectPreviewStatus.EXPIRED}
            )
        return record

    def read_artifact(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        artifact_id: UUID,
        now: datetime,
    ) -> DocumentConverterStoredArtifact:
        record = self.get_preview(owner_user_id=owner_user_id, preview_id=preview_id, now=now)
        if record.status is not DocumentConverterProjectPreviewStatus.SUCCEEDED:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Document Converter project preview artifact is not available.",
            )
        artifact = self.artifacts.get((owner_user_id, preview_id, artifact_id))
        if artifact is None:
            raise DomainError(
                code=ErrorCode.NOT_FOUND,
                message=f"DocumentConverterProjectPreviewArtifact not found: {artifact_id}",
            )
        return artifact

    def discard_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord:
        record = self.get_preview(owner_user_id=owner_user_id, preview_id=preview_id, now=now)
        discarded = record.model_copy(
            update={"status": DocumentConverterProjectPreviewStatus.DISCARDED}
        )
        self.records[(owner_user_id, preview_id)] = discarded
        return discarded

    def cleanup_expired(self, *, now: datetime) -> CleanupDocumentConverterProjectPreviewsResult:
        expired = [key for key, record in self.records.items() if record.expires_at <= now]
        for key in expired:
            self.records.pop(key)
        return CleanupDocumentConverterProjectPreviewsResult(
            deleted_previews=len(expired),
            deleted_artifacts=len(expired),
        )


async def _store_preview(
    *,
    actor,
    preview_id: UUID,
    store: InMemoryProjectPreviewStore,
    artifact_id: UUID | None = None,
    expires_at: datetime | None = None,
) -> None:
    renderer = RecordingProjectRenderer()
    handler = RenderDocumentConverterProjectPreviewHandler(
        renderer=renderer,
        previews=store,
        clock=FixedClock(datetime(2026, 6, 25, tzinfo=timezone.utc)),
        id_generator=SequenceIdGenerator([preview_id, artifact_id or uuid4(), uuid4(), uuid4()]),
    )
    result = await handler.handle(
        actor=actor, manifest=_manifest(output_mode="combined_pdf"), files=_uploads()
    )
    if expires_at is not None:
        record = store.records[(actor.id, result.preview_id)]
        store.records[(actor.id, result.preview_id)] = record.model_copy(
            update={"expires_at": expires_at}
        )
