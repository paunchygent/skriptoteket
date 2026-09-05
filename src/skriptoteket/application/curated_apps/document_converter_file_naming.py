"""Document Converter filename policy for save/export adoption.

Purpose:
    Apply the ST-37-05 save/export filename protocol to Document Converter
    outputs while the shared cross-app backend contract is still pending
    extraction.

Relationships:
    Used by Document Converter job, project-preview, download, and Vault-save
    handlers so browser UI may submit stem intent while backend application
    code remains the final filename, extension, and content-type authority.
"""

from __future__ import annotations

import unicodedata
from datetime import datetime
from pathlib import PurePosixPath
from typing import Protocol, TypeVar

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubOutputFormatV2
from skriptoteket.application.curated_apps.document_converter_projects import (
    DocumentConverterProjectManifest,
    DocumentConverterProjectOutputMode,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename

_OUTPUT_EXTENSIONS = {
    ConversionHubOutputFormatV2.MD: "md",
    ConversionHubOutputFormatV2.PDF: "pdf",
    ConversionHubOutputFormatV2.DOCX: "docx",
}
_OUTPUT_PURPOSE_LABELS = {
    ConversionHubOutputFormatV2.MD: "Markdown",
    ConversionHubOutputFormatV2.PDF: "Konverterad PDF",
    ConversionHubOutputFormatV2.DOCX: "Word-dokument",
}
_COMBINED_PROJECT_PURPOSE = "Sammanslagen PDF"
_SEPARATE_PROJECT_PURPOSE = "Separat PDF"
_MAX_FILENAME_LENGTH = 255
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class _FilenameArtifact(Protocol):
    """Represent immutable artifact models that can update their filename."""

    def model_copy(
        self: "_FilenameArtifactT",
        *,
        update: dict[str, str],
    ) -> "_FilenameArtifactT": ...


_FilenameArtifactT = TypeVar("_FilenameArtifactT", bound=_FilenameArtifact)


def build_single_file_protocol_filename(
    *,
    input_filename: str,
    output_format: ConversionHubOutputFormatV2,
    created_at: datetime,
    filename_stem: str | None = None,
) -> str:
    """Build the backend-authoritative filename for one converted document."""
    extension = _OUTPUT_EXTENSIONS[output_format]
    if filename_stem:
        return _filename_from_teacher_stem(filename_stem=filename_stem, extension=extension)
    return _default_protocol_filename(
        source_title=_source_title_from_filename(filename=input_filename),
        purpose_label=_OUTPUT_PURPOSE_LABELS[output_format],
        extension=extension,
        created_at=created_at,
    )


def apply_single_file_protocol_filename(
    *,
    artifact: _FilenameArtifactT,
    input_filename: str,
    output_format: ConversionHubOutputFormatV2,
    created_at: datetime,
    filename_stem: str | None = None,
) -> _FilenameArtifactT:
    """Return one artifact with its backend-owned Document Converter filename."""
    return artifact.model_copy(
        update={
            "filename": build_single_file_protocol_filename(
                input_filename=input_filename,
                output_format=output_format,
                created_at=created_at,
                filename_stem=filename_stem,
            )
        }
    )


def apply_project_preview_protocol_filenames(
    *,
    manifest: DocumentConverterProjectManifest,
    artifacts: list[_FilenameArtifactT],
    created_at: datetime,
) -> list[_FilenameArtifactT]:
    """Return project-preview artifacts with protocol filenames in render order."""
    filenames = _project_preview_filenames(manifest=manifest, created_at=created_at)
    return [
        artifact.model_copy(update={"filename": filename})
        for artifact, filename in zip(artifacts, filenames, strict=True)
    ]


def build_project_preview_filename_from_stem(*, filename_stem: str) -> str:
    """Build a project-preview filename from a teacher stem intent."""
    return _filename_from_teacher_stem(filename_stem=filename_stem, extension="pdf")


def disambiguate_filename(*, filename: str, existing_names: set[str]) -> str:
    """Append a bounded backend-owned ordinal when a saved output name already exists."""
    if filename not in existing_names:
        return filename

    path = PurePosixPath(filename)
    stem = path.stem
    suffix = path.suffix
    ordinal = 2
    while True:
        ordinal_suffix = f" ({ordinal}){suffix}"
        bounded_stem = _bound_collision_stem(
            stem=stem,
            max_length=_MAX_FILENAME_LENGTH - len(ordinal_suffix),
        )
        candidate = f"{bounded_stem}{ordinal_suffix}"
        if candidate not in existing_names:
            return candidate
        ordinal += 1


def _bound_collision_stem(*, stem: str, max_length: int) -> str:
    if len(stem) <= max_length:
        return stem

    source_stem, separator, purpose_label = stem.rpartition(" - ")
    preserved_label = f"{separator}{purpose_label}" if separator else ""
    available_source_length = max_length - len(preserved_label)
    if source_stem and available_source_length > 0:
        return f"{source_stem[:available_source_length]}{preserved_label}"
    return stem[:max_length]


def _default_protocol_filename(
    *,
    source_title: str,
    purpose_label: str,
    extension: str,
    created_at: datetime,
) -> str:
    stem = f"{source_title} - {purpose_label} - {created_at:%Y%m%d}"
    return _filename_from_teacher_stem(filename_stem=stem, extension=extension)


def _filename_from_teacher_stem(*, filename_stem: str, extension: str) -> str:
    normalized = unicodedata.normalize("NFC", filename_stem).strip()
    while normalized.lower().endswith(f".{extension.lower()}"):
        normalized = normalized[: -(len(extension) + 1)].rstrip()
    if not normalized:
        raise validation_error("Filename stem is required.")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise validation_error("Filename stem contains control characters.")
    final_filename = sanitize_input_filename(input_filename=f"{normalized}.{extension}")
    if PurePosixPath(final_filename).stem.upper() in _WINDOWS_RESERVED_NAMES:
        raise validation_error("Filename stem is reserved.")
    return final_filename


def _source_title_from_filename(*, filename: str) -> str:
    safe_filename = sanitize_input_filename(input_filename=filename)
    stem = PurePosixPath(safe_filename).stem.strip()
    if not stem:
        return "Dokument"
    return stem


def _project_preview_filenames(
    *,
    manifest: DocumentConverterProjectManifest,
    created_at: datetime,
) -> list[str]:
    filenames: list[str] = []
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.SEPARATE_PDFS,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        seen_titles: dict[str, int] = {}
        for entry in manifest.html_entries:
            base_title = (
                entry.title or _source_title_from_filename(filename=entry.filename)
            ).strip()
            seen_titles[base_title] = seen_titles.get(base_title, 0) + 1
            title = (
                base_title
                if seen_titles[base_title] == 1
                else f"{base_title} {seen_titles[base_title]}"
            )
            filenames.append(
                _default_protocol_filename(
                    source_title=title,
                    purpose_label=_SEPARATE_PROJECT_PURPOSE,
                    extension="pdf",
                    created_at=created_at,
                )
            )
    if manifest.output_mode in {
        DocumentConverterProjectOutputMode.COMBINED_PDF,
        DocumentConverterProjectOutputMode.BOTH,
    }:
        first_entry = manifest.html_entries[0]
        source_title = (
            first_entry.title or _source_title_from_filename(filename=first_entry.filename)
        ).strip()
        filenames.append(
            _default_protocol_filename(
                source_title=source_title,
                purpose_label=_COMBINED_PROJECT_PURPOSE,
                extension="pdf",
                created_at=created_at,
            )
        )
    return filenames
