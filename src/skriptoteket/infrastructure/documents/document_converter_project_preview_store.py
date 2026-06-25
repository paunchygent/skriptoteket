"""Filesystem store for Document Converter project preview artifacts.

Purpose:
    Persist owner-scoped HTML/CSS project preview metadata and PDF bytes under
    the server artifacts root with fail-closed writes and TTL cleanup.

Relationships:
    Implements the Document Converter project preview store protocol used by
    application handlers and the cron-friendly preview cleanup CLI.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.application.curated_apps.document_converter_projects import (
    CleanupDocumentConverterProjectPreviewsResult,
    DocumentConverterProjectPreviewRecord,
    DocumentConverterProjectPreviewStatus,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.document_converter import (
    DocumentConverterProjectPreviewStoreProtocol,
)

_METADATA_FILENAME = "preview.json"
_ARTIFACT_SUFFIX = ".bin"


class FilesystemDocumentConverterProjectPreviewStore(DocumentConverterProjectPreviewStoreProtocol):
    """Store project preview metadata and artifacts on the server filesystem."""

    def __init__(self, *, artifacts_root: Path) -> None:
        self._root = artifacts_root / "document-converter" / "project-previews"

    def store_preview(
        self,
        *,
        record: DocumentConverterProjectPreviewRecord,
        artifacts: list[DocumentConverterStoredArtifact],
    ) -> None:
        """Persist one preview record and its server-owned artifact bytes."""
        if len(record.artifacts) != len(artifacts):
            raise validation_error("Project preview metadata does not match artifacts.")
        preview_dir = self._preview_dir(
            owner_user_id=record.owner_user_id, preview_id=record.preview_id
        )
        staging_dir = _staging_preview_dir(preview_dir=preview_dir)
        try:
            staging_dir.mkdir(parents=True, exist_ok=False)
            for artifact_meta, artifact in zip(record.artifacts, artifacts, strict=True):
                _atomic_write_bytes(
                    path=_artifact_path(
                        preview_dir=staging_dir,
                        artifact_id=artifact_meta.artifact_id,
                    ),
                    content=artifact.content,
                )
            _write_record(preview_dir=staging_dir, record=record)
            staging_dir.replace(preview_dir)
        except Exception:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise

    def get_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord:
        """Return one owner-scoped preview or hide it as not found."""
        record = self._read_record(owner_user_id=owner_user_id, preview_id=preview_id)
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
        """Read one available preview artifact by owner, preview id, and artifact id."""
        record = self.get_preview(owner_user_id=owner_user_id, preview_id=preview_id, now=now)
        if record.status is not DocumentConverterProjectPreviewStatus.SUCCEEDED:
            raise validation_error("Document Converter project preview artifact is not available.")
        artifact_meta = next(
            (artifact for artifact in record.artifacts if artifact.artifact_id == artifact_id),
            None,
        )
        if artifact_meta is None:
            raise not_found("DocumentConverterProjectPreviewArtifact", str(artifact_id))
        content_path = _artifact_path(
            preview_dir=self._preview_dir(owner_user_id=owner_user_id, preview_id=preview_id),
            artifact_id=artifact_id,
        )
        if not content_path.is_file():
            raise not_found("DocumentConverterProjectPreviewArtifact", str(artifact_id))
        return DocumentConverterStoredArtifact(
            filename=artifact_meta.filename,
            content_type=artifact_meta.content_type,
            content=content_path.read_bytes(),
        )

    def discard_preview(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
        now: datetime,
    ) -> DocumentConverterProjectPreviewRecord:
        """Mark a preview discarded and remove artifact bytes."""
        record = self.get_preview(owner_user_id=owner_user_id, preview_id=preview_id, now=now)
        preview_dir = self._preview_dir(owner_user_id=owner_user_id, preview_id=preview_id)
        for artifact in record.artifacts:
            _artifact_path(preview_dir=preview_dir, artifact_id=artifact.artifact_id).unlink(
                missing_ok=True
            )
        discarded = record.model_copy(
            update={"status": DocumentConverterProjectPreviewStatus.DISCARDED}
        )
        _write_record(preview_dir=preview_dir, record=discarded)
        return discarded

    def cleanup_expired(
        self,
        *,
        now: datetime,
    ) -> CleanupDocumentConverterProjectPreviewsResult:
        """Delete expired previews and malformed orphan directories."""
        deleted_previews = 0
        deleted_artifacts = 0
        if not self._root.exists():
            return CleanupDocumentConverterProjectPreviewsResult(
                deleted_previews=0,
                deleted_artifacts=0,
            )
        for owner_dir in self._root.iterdir():
            if not owner_dir.is_dir():
                continue
            for preview_dir in owner_dir.iterdir():
                if not preview_dir.is_dir():
                    continue
                if not _should_delete_preview_dir(preview_dir=preview_dir, now=now):
                    continue
                deleted_artifacts += len(list(preview_dir.glob(f"*{_ARTIFACT_SUFFIX}")))
                shutil.rmtree(preview_dir, ignore_errors=True)
                deleted_previews += 1
            _remove_empty_parent(owner_dir)
        return CleanupDocumentConverterProjectPreviewsResult(
            deleted_previews=deleted_previews,
            deleted_artifacts=deleted_artifacts,
        )

    def _read_record(
        self,
        *,
        owner_user_id: UUID,
        preview_id: UUID,
    ) -> DocumentConverterProjectPreviewRecord:
        metadata_path = (
            self._preview_dir(owner_user_id=owner_user_id, preview_id=preview_id)
            / _METADATA_FILENAME
        )
        if not metadata_path.is_file():
            raise not_found("DocumentConverterProjectPreview", str(preview_id))
        try:
            return DocumentConverterProjectPreviewRecord.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise validation_error(
                "Document Converter project preview metadata is invalid."
            ) from exc

    def _preview_dir(self, *, owner_user_id: UUID, preview_id: UUID) -> Path:
        candidate = (self._root / str(owner_user_id) / str(preview_id)).resolve()
        root = self._root.resolve()
        if root not in candidate.parents and root != candidate:
            raise validation_error("Document Converter project preview path is invalid.")
        return candidate


def _artifact_path(*, preview_dir: Path, artifact_id: UUID) -> Path:
    return preview_dir / f"{artifact_id}{_ARTIFACT_SUFFIX}"


def _staging_preview_dir(*, preview_dir: Path) -> Path:
    return preview_dir.with_name(f".{preview_dir.name}.tmp-{uuid4()}")


def _should_delete_preview_dir(*, preview_dir: Path, now: datetime) -> bool:
    if preview_dir.name.startswith(".") and ".tmp-" in preview_dir.name:
        return True
    metadata_path = preview_dir / _METADATA_FILENAME
    if not metadata_path.is_file():
        return True
    try:
        record = DocumentConverterProjectPreviewRecord.model_validate_json(
            metadata_path.read_text(encoding="utf-8")
        )
    except Exception:
        return True
    return record.expires_at <= now


def _write_record(
    *,
    preview_dir: Path,
    record: DocumentConverterProjectPreviewRecord,
) -> None:
    _atomic_write_text(
        path=preview_dir / _METADATA_FILENAME,
        content=record.model_dump_json(),
    )


def _atomic_write_bytes(*, path: Path, content: bytes) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp-{uuid4()}")
    try:
        tmp_path.write_bytes(content)
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _atomic_write_text(*, path: Path, content: str) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp-{uuid4()}")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _remove_empty_parent(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        return
