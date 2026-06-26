"""Document Converter HTML/CSS project preview contracts.

Purpose:
    Define the route-inactive Document Converter project manifest, PDF controls,
    temporary preview lifecycle, and server-owned artifact response models for
    HTML/CSS-to-PDF project rendering.

Relationships:
    Used by the scoped Conversion Hub Document Converter API, project preview
    handlers, infrastructure preview storage, and the sandboxed WeasyPrint
    project renderer.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubPdfOrientationV2,
    ConversionHubPdfPaperSizeV2,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.domain.errors import validation_error

DOCUMENT_CONVERTER_PROJECT_MAX_HTML_ENTRIES = 10
DOCUMENT_CONVERTER_PROJECT_MAX_CSS_FILES = 10
DOCUMENT_CONVERTER_PROJECT_MAX_IMAGE_FILES = 20
DOCUMENT_CONVERTER_PROJECT_MAX_FONT_FILES = 0
DOCUMENT_CONVERTER_PROJECT_PREVIEW_TTL_SECONDS = 60 * 60 * 24
DOCUMENT_CONVERTER_PROJECT_BASE_URL = "project:///"

_GENERIC_CONTENT_TYPES = frozenset({"", "application/octet-stream"})
_HTML_SUFFIXES = frozenset({".html", ".htm"})
_CSS_SUFFIXES = frozenset({".css"})
_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
_HTML_CONTENT_TYPES = frozenset({"application/xhtml+xml", "text/html"})
_CSS_CONTENT_TYPES = frozenset({"text/css"})
_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


class DocumentConverterProjectOutputMode(StrEnum):
    """Select which preview PDF artifacts the renderer should create."""

    SEPARATE_PDFS = "separate_pdfs"
    COMBINED_PDF = "combined_pdf"
    BOTH = "both"


class DocumentConverterProjectTemplateId(StrEnum):
    """Internal first template identifiers for the preview contract."""

    ACADEMIC_PHD = "academic_phd"
    CLEAN_WORKSHEET = "clean_worksheet"
    EXPRESSIVE_HANDOUT = "expressive_handout"


class DocumentConverterProjectPreviewStatus(StrEnum):
    """Represent the temporary project preview lifecycle."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DISCARDED = "discarded"
    EXPIRED = "expired"


class DocumentConverterProjectPreviewArtifactKind(StrEnum):
    """Identify one preview artifact in the output-mode response."""

    SEPARATE_PDF = "separate_pdf"
    COMBINED_PDF = "combined_pdf"


class DocumentConverterProjectMargins(BaseModel):
    """Represent per-side PDF page margins in millimeters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    top_mm: int = Field(default=12, ge=0, le=50)
    right_mm: int = Field(default=12, ge=0, le=50)
    bottom_mm: int = Field(default=12, ge=0, le=50)
    left_mm: int = Field(default=12, ge=0, le=50)


class DocumentConverterProjectPdfControls(BaseModel):
    """Represent non-copy PDF controls for project preview rendering."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    paper_size: ConversionHubPdfPaperSizeV2 = ConversionHubPdfPaperSizeV2.A4
    orientation: ConversionHubPdfOrientationV2 = ConversionHubPdfOrientationV2.PORTRAIT
    margins: DocumentConverterProjectMargins = Field(
        default_factory=DocumentConverterProjectMargins
    )
    template_id: DocumentConverterProjectTemplateId = (
        DocumentConverterProjectTemplateId.ACADEMIC_PHD
    )


class DocumentConverterProjectHtmlEntry(BaseModel):
    """Represent one HTML source document inside a preview project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_id: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("entry_id")
    @classmethod
    def _validate_entry_id(cls, value: str) -> str:
        if not all(character.isalnum() or character in {"-", "_"} for character in value):
            raise ValueError("entry_id must contain only letters, numbers, hyphens, or underscores")
        return value

    @field_validator("filename")
    @classmethod
    def _validate_html_filename(cls, value: str) -> str:
        return _validate_project_filename(value=value, allowed_suffixes=_HTML_SUFFIXES)


class DocumentConverterProjectUploadedFile(BaseModel):
    """Represent one uploaded project file after web-boundary reads are capped."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    content: bytes = Field(min_length=1)


class DocumentConverterProjectManifest(BaseModel):
    """Define the first route-inactive HTML/CSS project preview manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    html_entries: list[DocumentConverterProjectHtmlEntry] = Field(
        min_length=1,
        max_length=DOCUMENT_CONVERTER_PROJECT_MAX_HTML_ENTRIES,
    )
    css_files: list[str] = Field(
        default_factory=list,
        max_length=DOCUMENT_CONVERTER_PROJECT_MAX_CSS_FILES,
    )
    image_files: list[str] = Field(
        default_factory=list,
        max_length=DOCUMENT_CONVERTER_PROJECT_MAX_IMAGE_FILES,
    )
    font_files: list[str] = Field(default_factory=list)
    output_mode: DocumentConverterProjectOutputMode = DocumentConverterProjectOutputMode.BOTH
    pdf_controls: DocumentConverterProjectPdfControls = Field(
        default_factory=DocumentConverterProjectPdfControls
    )

    @field_validator("css_files")
    @classmethod
    def _validate_css_filenames(cls, values: list[str]) -> list[str]:
        return [
            _validate_project_filename(value=value, allowed_suffixes=_CSS_SUFFIXES)
            for value in values
        ]

    @field_validator("image_files")
    @classmethod
    def _validate_image_filenames(cls, values: list[str]) -> list[str]:
        return [
            _validate_project_filename(value=value, allowed_suffixes=_IMAGE_SUFFIXES)
            for value in values
        ]

    @field_validator("font_files")
    @classmethod
    def _validate_font_filenames(cls, values: list[str]) -> list[str]:
        if values:
            raise ValueError(
                "font_files supports at most "
                f"{DOCUMENT_CONVERTER_PROJECT_MAX_FONT_FILES} uploaded files"
            )
        return values

    @model_validator(mode="after")
    def _validate_unique_manifest_names(self) -> "DocumentConverterProjectManifest":
        names = self.expected_filenames()
        if len(names) != self.expected_file_count:
            raise ValueError("Project manifest filenames must be unique")
        entry_ids = [entry.entry_id for entry in self.html_entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("Project manifest entry_id values must be unique")
        return self

    @property
    def expected_file_count(self) -> int:
        """Return the exact number of files this manifest declares."""
        return len(self.html_entries) + len(self.css_files) + len(self.image_files)

    def expected_filenames(self) -> set[str]:
        """Return the declared upload filenames for this project."""
        return {
            *(entry.filename for entry in self.html_entries),
            *self.css_files,
            *self.image_files,
        }

    def validate_uploaded_file_set(self, *, uploaded_filenames: set[str]) -> None:
        """Reject missing or undeclared uploaded project files."""
        expected = self.expected_filenames()
        missing = sorted(expected - uploaded_filenames)
        unexpected = sorted(uploaded_filenames - expected)
        if missing or unexpected:
            raise validation_error(
                "Document Converter project uploads must match the manifest.",
                details={
                    "missing_filenames": missing,
                    "unexpected_filenames": unexpected,
                },
            )


class DocumentConverterProjectPreviewArtifact(BaseModel):
    """Describe one server-owned temporary preview artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: UUID
    kind: DocumentConverterProjectPreviewArtifactKind
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=1)
    source_entry_id: str | None = Field(default=None, min_length=1, max_length=64)
    download_url: str | None = Field(default=None, max_length=512)


class DocumentConverterProjectPreviewRecord(BaseModel):
    """Persist one owner-scoped temporary project preview record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    preview_id: UUID
    owner_user_id: UUID
    status: DocumentConverterProjectPreviewStatus
    output_mode: DocumentConverterProjectOutputMode
    created_at: datetime
    expires_at: datetime
    artifacts: list[DocumentConverterProjectPreviewArtifact]
    template_id: DocumentConverterProjectTemplateId
    error: str | None = None


class DocumentConverterProjectPreviewResult(BaseModel):
    """Return project preview status plus server-owned artifact metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    preview_id: UUID
    status: DocumentConverterProjectPreviewStatus
    output_mode: DocumentConverterProjectOutputMode
    created_at: datetime
    expires_at: datetime
    artifacts: list[DocumentConverterProjectPreviewArtifact]
    template_id: DocumentConverterProjectTemplateId
    error: str | None = None


class DiscardDocumentConverterProjectPreviewResult(BaseModel):
    """Return the discarded temporary preview status."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    preview_id: UUID
    status: DocumentConverterProjectPreviewStatus


class CleanupDocumentConverterProjectPreviewsResult(BaseModel):
    """Return temporary preview cleanup counts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    deleted_previews: int = Field(ge=0)
    deleted_artifacts: int = Field(ge=0)


class SaveDocumentConverterProjectPreviewArtifactResult(BaseModel):
    """Return the Mina filer record created from an explicit preview save."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vault_artifact: ConversionHubSavedVaultArtifact
    source_artifact_id: str


def validate_document_converter_project_upload(
    *,
    manifest: DocumentConverterProjectManifest,
    filename: str | None,
    content_type: str | None,
) -> tuple[str, str]:
    """Validate one uploaded project file against the manifest asset model."""
    normalized_filename = _validate_declared_filename(manifest=manifest, filename=filename)
    normalized_content_type = (content_type or "application/octet-stream").strip().lower()
    allowed_content_types = _allowed_content_types(manifest=manifest, filename=normalized_filename)
    if (
        normalized_content_type not in allowed_content_types
        and normalized_content_type not in _GENERIC_CONTENT_TYPES
    ):
        raise validation_error(
            "Document Converter project content type does not match the manifest asset.",
            details={
                "filename": normalized_filename,
                "content_type": normalized_content_type,
                "allowed_content_types": sorted(allowed_content_types),
            },
        )
    return normalized_filename, normalized_content_type or "application/octet-stream"


def build_document_converter_project_preview_source_artifact_id(
    *,
    preview_id: UUID,
    artifact_id: UUID,
) -> str:
    """Build the stable Vault source id for an explicit project preview save."""
    return f"document-converter:project-preview:{preview_id}:{artifact_id}"


def _validate_declared_filename(
    *,
    manifest: DocumentConverterProjectManifest,
    filename: str | None,
) -> str:
    normalized_filename = (filename or "").strip()
    if not normalized_filename:
        raise validation_error("Uploaded project file is missing a filename.")
    if normalized_filename not in manifest.expected_filenames():
        raise validation_error(
            "Uploaded project file is not declared in the manifest.",
            details={"filename": normalized_filename},
        )
    return normalized_filename


def _allowed_content_types(
    *,
    manifest: DocumentConverterProjectManifest,
    filename: str,
) -> frozenset[str]:
    html_filenames = {entry.filename for entry in manifest.html_entries}
    if filename in html_filenames:
        return _HTML_CONTENT_TYPES
    if filename in manifest.css_files:
        return _CSS_CONTENT_TYPES
    if filename in manifest.image_files:
        return _IMAGE_CONTENT_TYPES
    return frozenset()


def _validate_project_filename(*, value: str, allowed_suffixes: frozenset[str]) -> str:
    stripped = value.strip()
    path = PurePosixPath(stripped)
    if (
        not stripped
        or stripped != path.name
        or "/" in stripped
        or "\\" in stripped
        or path.is_absolute()
        or stripped in {".", ".."}
    ):
        raise ValueError("Project asset filenames must be bare filenames")
    lower_name = stripped.lower()
    if not any(lower_name.endswith(suffix) for suffix in allowed_suffixes):
        raise ValueError("Project asset filename suffix is not supported")
    return stripped
