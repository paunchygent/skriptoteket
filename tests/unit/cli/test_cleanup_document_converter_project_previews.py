"""CLI tests for Document Converter project preview cleanup.

Purpose:
    Prove operators have a cron-friendly entrypoint that enforces temporary
    HTML/CSS project preview retention under the artifacts root.

Relationships:
    Exercises the Typer CLI surface registered in ``skriptoteket.cli.main`` and
    verifies deletion through the filesystem preview store used by the
    route-inactive Document Converter project preview contract.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from typer.testing import CliRunner

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectOutputMode,
    DocumentConverterProjectPreviewArtifact,
    DocumentConverterProjectPreviewArtifactKind,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectPreviewStatus,
)
from skriptoteket.cli.main import app
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.documents.document_converter_project_preview_store import (
    FilesystemDocumentConverterProjectPreviewStore,
)


def test_cleanup_project_previews_command_deletes_expired_directories(tmp_path) -> None:
    """The production CLI entrypoint should enforce preview TTL cleanup."""
    now = datetime.now(timezone.utc)
    owner_id = uuid4()
    expired_preview_id = uuid4()
    active_preview_id = uuid4()
    store = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=tmp_path)
    store.store_preview(
        record=_record(
            owner_id=owner_id,
            preview_id=expired_preview_id,
            artifact_id=uuid4(),
            expires_at=now - timedelta(minutes=1),
        ),
        artifacts=[_artifact(filename="expired.pdf", content=b"%PDF-EXPIRED")],
    )
    store.store_preview(
        record=_record(
            owner_id=owner_id,
            preview_id=active_preview_id,
            artifact_id=uuid4(),
            expires_at=now + timedelta(hours=1),
        ),
        artifacts=[_artifact(filename="active.pdf", content=b"%PDF-ACTIVE")],
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "cleanup-document-converter-project-previews",
            "--artifacts-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "deleted_previews=1" in result.output
    assert "deleted_artifacts=1" in result.output
    with pytest.raises(DomainError):
        store.get_preview(owner_user_id=owner_id, preview_id=expired_preview_id, now=now)
    assert store.get_preview(owner_user_id=owner_id, preview_id=active_preview_id, now=now)


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
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
        artifacts=[
            DocumentConverterProjectPreviewArtifact(
                artifact_id=artifact_id,
                kind=DocumentConverterProjectPreviewArtifactKind.COMBINED_PDF,
                filename="preview.pdf",
                content_type="application/pdf",
                size_bytes=12,
                source_entry_id=None,
                download_url=None,
            )
        ],
        template_id="academic_phd",
        error=None,
    )


def _artifact(*, filename: str, content: bytes) -> DocumentConverterStoredArtifact:
    return DocumentConverterStoredArtifact(
        filename=filename,
        content_type="application/pdf",
        content=content,
    )
