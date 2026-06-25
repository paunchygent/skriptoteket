"""Infrastructure tests for Document Converter project previews.

Purpose:
    Prove temporary HTML/CSS preview artifacts are stored under server-owned
    authority and linked assets are fetched only from the uploaded project map.

Relationships:
    Exercises the filesystem preview store and WeasyPrint project URL fetcher
    used by the route-inactive Document Converter project preview contract.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from weasyprint.urls import FatalURLFetchingError

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectPreviewArtifact,
    DocumentConverterProjectPreviewArtifactKind,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectPreviewStatus,
    DocumentConverterProjectUploadedFile,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.documents import (
    document_converter_project_preview_store as store_module,
)
from skriptoteket.infrastructure.documents import (
    document_converter_project_previews as preview_module,
)
from skriptoteket.infrastructure.documents.document_converter_project_previews import (
    DocumentConverterProjectAssetFetcher,
    FilesystemDocumentConverterProjectPreviewStore,
    WeasyPrintDocumentConverterProjectRenderer,
)


def test_project_asset_fetcher_resolves_declared_filenames_only() -> None:
    fetcher = DocumentConverterProjectAssetFetcher(
        files=[
            DocumentConverterProjectUploadedFile(
                filename="style.css",
                content_type="text/css",
                content=b"h1 { color: black; }",
            ),
            DocumentConverterProjectUploadedFile(
                filename="logo.png",
                content_type="image/png",
                content=b"png",
            ),
        ]
    )

    response = fetcher.fetch("project:///logo.png")

    assert response.content_type == "image/png"
    assert response.read() == b"png"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://example.test/logo.png",
        "project:///../secret.png",
        "project:///nested/logo.png",
        "project:///missing.png",
    ],
)
def test_project_asset_fetcher_rejects_external_or_undeclared_urls(url: str) -> None:
    fetcher = DocumentConverterProjectAssetFetcher(
        files=[
            DocumentConverterProjectUploadedFile(
                filename="logo.png",
                content_type="image/png",
                content=b"png",
            )
        ]
    )

    with pytest.raises(FatalURLFetchingError):
        fetcher.fetch(url)


@pytest.mark.parametrize(
    ("output_mode", "filenames"),
    [
        ("separate_pdfs", ["one.pdf", "two.pdf"]),
        ("combined_pdf", ["combined.pdf"]),
        ("both", ["one.pdf", "two.pdf", "combined.pdf"]),
    ],
)
def test_project_renderer_selects_requested_output_mode(
    monkeypatch,
    output_mode: str,
    filenames: list[str],
) -> None:
    monkeypatch.setattr(
        preview_module,
        "_render_weasyprint_pdf",
        lambda *, html, css_text, fetcher: f"%PDF-{html}".encode("utf-8"),
    )
    monkeypatch.setattr(
        preview_module,
        "_combine_pdf_bytes",
        lambda artifacts: b"%PDF-COMBINED",
    )
    renderer = WeasyPrintDocumentConverterProjectRenderer()

    artifacts = renderer.render_project(
        manifest=_manifest(output_mode=output_mode),
        files=_project_files(),
    )

    assert [artifact.filename for artifact in artifacts] == filenames
    assert all(artifact.content_type == "application/pdf" for artifact in artifacts)


def test_filesystem_project_preview_store_round_trips_owner_scoped_artifact(tmp_path) -> None:
    owner_id = uuid4()
    preview_id = uuid4()
    artifact_id = uuid4()
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)
    record = _record(
        owner_id=owner_id,
        preview_id=preview_id,
        artifact_id=artifact_id,
        expires_at=now + timedelta(hours=24),
    )
    artifact = DocumentConverterStoredArtifact(
        filename="preview.pdf",
        content_type="application/pdf",
        content=b"%PDF-PREVIEW",
    )

    store.store_preview(record=record, artifacts=[artifact])

    loaded = store.get_preview(owner_user_id=owner_id, preview_id=preview_id, now=now)
    restored = store.read_artifact(
        owner_user_id=owner_id,
        preview_id=preview_id,
        artifact_id=artifact_id,
        now=now,
    )
    assert loaded.preview_id == preview_id
    assert loaded.artifacts[0].artifact_id == artifact_id
    assert restored.content == b"%PDF-PREVIEW"


def test_filesystem_project_preview_store_hides_foreign_owner(tmp_path) -> None:
    owner_id = uuid4()
    preview_id = uuid4()
    artifact_id = uuid4()
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)
    store.store_preview(
        record=_record(
            owner_id=owner_id,
            preview_id=preview_id,
            artifact_id=artifact_id,
            expires_at=now + timedelta(hours=24),
        ),
        artifacts=[
            DocumentConverterStoredArtifact(
                filename="preview.pdf",
                content_type="application/pdf",
                content=b"%PDF-PREVIEW",
            )
        ],
    )

    with pytest.raises(DomainError) as excinfo:
        store.get_preview(owner_user_id=uuid4(), preview_id=preview_id, now=now)

    assert excinfo.value.code is ErrorCode.NOT_FOUND


def test_filesystem_project_preview_store_cleans_expired_previews(tmp_path) -> None:
    owner_id = uuid4()
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    expired_preview_id = uuid4()
    active_preview_id = uuid4()
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)
    store.store_preview(
        record=_record(
            owner_id=owner_id,
            preview_id=expired_preview_id,
            artifact_id=uuid4(),
            expires_at=now - timedelta(seconds=1),
        ),
        artifacts=[
            DocumentConverterStoredArtifact(
                filename="expired.pdf",
                content_type="application/pdf",
                content=b"%PDF-EXPIRED",
            )
        ],
    )
    store.store_preview(
        record=_record(
            owner_id=owner_id,
            preview_id=active_preview_id,
            artifact_id=uuid4(),
            expires_at=now + timedelta(hours=1),
        ),
        artifacts=[
            DocumentConverterStoredArtifact(
                filename="active.pdf",
                content_type="application/pdf",
                content=b"%PDF-ACTIVE",
            )
        ],
    )

    result = store.cleanup_expired(now=now)

    assert result.deleted_previews == 1
    with pytest.raises(DomainError):
        store.get_preview(owner_user_id=owner_id, preview_id=expired_preview_id, now=now)
    assert store.get_preview(owner_user_id=owner_id, preview_id=active_preview_id, now=now)


def test_filesystem_project_preview_store_rolls_back_artifacts_when_metadata_write_fails(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = uuid4()
    preview_id = uuid4()
    artifact_id = uuid4()
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)
    preview_dir = (
        tmp_path / "document-converter" / "project-previews" / str(owner_id) / str(preview_id)
    )

    def fail_record_write(*, preview_dir, record) -> None:
        del preview_dir, record
        raise OSError("metadata write failed")

    monkeypatch.setattr(store_module, "_write_record", fail_record_write)

    with pytest.raises(OSError):
        store.store_preview(
            record=_record(
                owner_id=owner_id,
                preview_id=preview_id,
                artifact_id=artifact_id,
                expires_at=now + timedelta(hours=24),
            ),
            artifacts=[
                DocumentConverterStoredArtifact(
                    filename="preview.pdf",
                    content_type="application/pdf",
                    content=b"%PDF-PARTIAL",
                )
            ],
        )

    assert not preview_dir.exists()
    assert list((tmp_path / "document-converter").rglob("*.bin")) == []


def test_filesystem_project_preview_store_cleans_malformed_orphan_preview_directories(
    tmp_path,
) -> None:
    owner_id = uuid4()
    now = datetime(2026, 6, 25, tzinfo=timezone.utc)
    malformed_preview_dir = (
        tmp_path / "document-converter" / "project-previews" / str(owner_id) / str(uuid4())
    )
    orphan_preview_dir = (
        tmp_path / "document-converter" / "project-previews" / str(owner_id) / str(uuid4())
    )
    malformed_preview_dir.mkdir(parents=True)
    orphan_preview_dir.mkdir(parents=True)
    (malformed_preview_dir / "preview.json").write_text("{not-json", encoding="utf-8")
    (malformed_preview_dir / f"{uuid4()}.bin").write_bytes(b"%PDF-MALFORMED")
    (orphan_preview_dir / f"{uuid4()}.bin").write_bytes(b"%PDF-ORPHAN")
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)

    result = store.cleanup_expired(now=now)

    assert result.deleted_previews == 2
    assert result.deleted_artifacts == 2
    assert not malformed_preview_dir.exists()
    assert not orphan_preview_dir.exists()


def _record(
    *,
    owner_id,
    preview_id,
    artifact_id,
    expires_at: datetime,
) -> DocumentConverterProjectPreviewRecord:
    return DocumentConverterProjectPreviewRecord(
        preview_id=preview_id,
        owner_user_id=owner_id,
        status=DocumentConverterProjectPreviewStatus.SUCCEEDED,
        output_mode=DocumentConverterProjectOutputMode.COMBINED_PDF,
        created_at=datetime(2026, 6, 25, tzinfo=timezone.utc),
        expires_at=expires_at,
        artifacts=[
            DocumentConverterProjectPreviewArtifact(
                artifact_id=artifact_id,
                kind=DocumentConverterProjectPreviewArtifactKind.COMBINED_PDF,
                filename="preview.pdf",
                content_type="application/pdf",
                size_bytes=len(b"%PDF-PREVIEW"),
                source_entry_id=None,
                download_url=None,
            )
        ],
        template_id="academic_phd",
        error=None,
    )


def _manifest(*, output_mode: str) -> DocumentConverterProjectManifest:
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


def _project_files() -> list[DocumentConverterProjectUploadedFile]:
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
            content=b"h1 { color: black; }",
        ),
        DocumentConverterProjectUploadedFile(
            filename="logo.png",
            content_type="image/png",
            content=b"png",
        ),
    ]
