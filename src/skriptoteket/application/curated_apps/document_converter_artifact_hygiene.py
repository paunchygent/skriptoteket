"""Document Converter teacher-facing artifact hygiene contract.

Purpose:
    Validate terminal Document Converter artifacts before preview, download, or
    save can expose them as teacher files.

Relationships:
    Used by Document Converter application handlers after local or Sir Convert
    producer bytes are fetched and before those bytes cross into HTTP responses
    or Vault persistence.
"""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable
from uuid import UUID

from skriptoteket.application.curated_apps.document_converter import (
    DocumentConverterStoredArtifact,
)
from skriptoteket.domain.errors import validation_error

_FORBIDDEN_TEXT_MARKERS = (
    "pdf_checkpointed_output",
    "sir-convert-a-lot:partial",
    "__missing_asset__",
    "Bild saknas",
    "Saknad resurs",
    "document-converter:project-preview:",
    "file:///Users/",
    "file:///private/",
    "file:///tmp/",
    "/Users/",
    "/private/var/",
    "/var/folders/",
    "\\Users\\",
)
_TEXT_ZIP_SUFFIXES = frozenset({".xml", ".rels", ".html", ".htm", ".md", ".txt"})
_MAX_ZIP_MEMBER_BYTES = 1_000_000


def validate_document_converter_teacher_artifact(
    *,
    artifact: DocumentConverterStoredArtifact,
    job_id: UUID | None = None,
    upstream_job_id: str | None = None,
    source_artifact_id: str | None = None,
    additional_internal_markers: Iterable[str] = (),
) -> None:
    """Reject terminal Document Converter artifacts with internal markers.

    Args:
        artifact: Terminal artifact fetched from the selected producer.
        job_id: Local owner-scoped job id; this must not leak into artifact bytes.
        upstream_job_id: Producer job id; this must not leak into artifact bytes.
        source_artifact_id: Internal Vault provenance id for the artifact.
        additional_internal_markers: Other caller-owned ids that must not leak.

    Raises:
        DomainError: If the artifact contains known teacher-facing hygiene
            violations.
    """
    dynamic_markers = tuple(
        marker
        for marker in (
            str(job_id) if job_id is not None else None,
            upstream_job_id,
            source_artifact_id,
            *additional_internal_markers,
        )
        if marker is not None and marker
    )
    markers = (*_FORBIDDEN_TEXT_MARKERS, *dynamic_markers)
    for surface in _artifact_text_surfaces(artifact):
        if _contains_forbidden_marker(surface=surface, markers=markers):
            raise validation_error(
                "Konverteringsresultatet innehåller intern diagnostik och kan inte användas."
            )


def _artifact_text_surfaces(artifact: DocumentConverterStoredArtifact) -> Iterable[str]:
    yield artifact.filename
    yield artifact.content_type
    yield artifact.content.decode("utf-8", errors="ignore")
    yield from _zip_text_surfaces(content=artifact.content)


def _zip_text_surfaces(*, content: bytes) -> Iterable[str]:
    if not zipfile.is_zipfile(io.BytesIO(content)):
        return
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for member in archive.infolist():
            if member.file_size > _MAX_ZIP_MEMBER_BYTES:
                continue
            if not _is_text_zip_member(member.filename):
                continue
            yield archive.read(member).decode("utf-8", errors="ignore")


def _is_text_zip_member(filename: str) -> bool:
    lower_name = filename.lower()
    return any(lower_name.endswith(suffix) for suffix in _TEXT_ZIP_SUFFIXES)


def _contains_forbidden_marker(*, surface: str, markers: tuple[str, ...]) -> bool:
    return any(marker in surface for marker in markers)
