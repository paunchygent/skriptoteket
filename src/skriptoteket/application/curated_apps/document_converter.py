"""Document Converter MVP contracts for scoped Conversion Hub APIs.

Purpose:
    Define the authenticated Document Converter backend contract that sits
    under the existing ``documents.conversion_hub`` technical app id while
    remaining separate from Exam Converter and Audio Transcription workflows.

Relationships:
    Used by ``web.api.v1.apps_conversion_hub`` for response serialization and
    by ``handlers.conversion_hub_document_converter`` for owner-scoped artifact
    authorization, result summaries, and Vault source-artifact identity.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubJobSpecV2,
    ConversionHubJobStatus,
    ConversionHubListRoutesResult,
    ConversionHubOutputFormatV2,
    ConversionHubRouteV2,
    ConversionHubSourceFormatV2,
)
from skriptoteket.application.curated_apps.conversion_hub_saved_artifacts import (
    ConversionHubSavedVaultArtifact,
)
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename

DOCUMENT_CONVERTER_ARTIFACT_KEY = "converted_document"
DOCUMENT_CONVERTER_MAX_BATCH_ITEMS = 10
LOCAL_DOCUMENT_CONVERTER_PRODUCER_PREFIX = "local:"

_DOCUMENT_ROUTES = (
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.MD,
        title="PDF -> Markdown",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.PDF,
        output_format=ConversionHubOutputFormatV2.DOCX,
        title="PDF -> DOCX",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.DOCX,
        output_format=ConversionHubOutputFormatV2.MD,
        title="DOCX -> Markdown",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.DOCX,
        output_format=ConversionHubOutputFormatV2.PDF,
        title="DOCX -> PDF",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.MD,
        output_format=ConversionHubOutputFormatV2.PDF,
        title="Markdown -> PDF",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.MD,
        output_format=ConversionHubOutputFormatV2.DOCX,
        title="Markdown -> DOCX",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.MD,
        title="HTML -> Markdown",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.PDF,
        title="HTML -> PDF",
    ),
    ConversionHubRouteV2(
        source_format=ConversionHubSourceFormatV2.HTML,
        output_format=ConversionHubOutputFormatV2.DOCX,
        title="HTML -> DOCX",
    ),
)
_DOCUMENT_ROUTE_PAIRS = frozenset(
    (route.source_format, route.output_format) for route in _DOCUMENT_ROUTES
)
_OUTPUT_EXTENSIONS = {
    ConversionHubOutputFormatV2.MD: "md",
    ConversionHubOutputFormatV2.PDF: "pdf",
    ConversionHubOutputFormatV2.DOCX: "docx",
}
_GENERIC_UPLOAD_CONTENT_TYPES = frozenset({"", "application/octet-stream"})
_SOURCE_UPLOAD_SUFFIXES = {
    ConversionHubSourceFormatV2.PDF: frozenset({".pdf"}),
    ConversionHubSourceFormatV2.DOCX: frozenset({".docx"}),
    ConversionHubSourceFormatV2.MD: frozenset({".md", ".markdown"}),
    ConversionHubSourceFormatV2.HTML: frozenset({".html", ".htm"}),
}
_SOURCE_UPLOAD_CONTENT_TYPES = {
    ConversionHubSourceFormatV2.PDF: frozenset({"application/pdf"}),
    ConversionHubSourceFormatV2.DOCX: frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    ),
    ConversionHubSourceFormatV2.MD: frozenset({"text/markdown", "text/plain", "text/x-markdown"}),
    ConversionHubSourceFormatV2.HTML: frozenset({"application/xhtml+xml", "text/html"}),
}
_OUTPUT_CONTENT_TYPES = {
    ConversionHubOutputFormatV2.MD: "text/markdown; charset=utf-8",
    ConversionHubOutputFormatV2.PDF: "application/pdf",
    ConversionHubOutputFormatV2.DOCX: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}


class DocumentConverterProducerKind(StrEnum):
    """Identify the backend producer selected for one Document Converter item."""

    LOCAL = "local"
    SIR_CONVERT = "sir_convert"


class DocumentConverterProducerDecision(BaseModel):
    """Explain the automatic producer decision for one validated item."""

    model_config = ConfigDict(frozen=True)

    producer: DocumentConverterProducerKind
    reason: str = Field(min_length=1, max_length=128)


class DocumentConverterStoredArtifact(BaseModel):
    """Represent one server-owned local Document Converter result."""

    model_config = ConfigDict(frozen=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    content: bytes = Field(min_length=1)


class DocumentConverterSubmittedJob(BaseModel):
    """Return one local job plus the automatic producer decision."""

    model_config = ConfigDict(extra="forbid")

    input_filename: str = Field(min_length=1)
    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None
    producer: DocumentConverterProducerKind
    producer_reason: str = Field(min_length=1, max_length=128)


class DocumentConverterSubmitResult(BaseModel):
    """Return all local jobs created from one Document Converter batch request."""

    model_config = ConfigDict(extra="forbid")

    jobs: list[DocumentConverterSubmittedJob]


class DocumentConverterResultArtifact(BaseModel):
    """Describe the single converted artifact after a successful MVP job."""

    model_config = ConfigDict(frozen=True)

    filename: str | None = Field(default=None, min_length=1, max_length=255)
    content_type: str | None = Field(default=None, min_length=1, max_length=255)
    size_bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    source_artifact_id: str = Field(min_length=1, max_length=255)


class DocumentConverterJobStatusResult(BaseModel):
    """Return local status plus the default result artifact once it exists."""

    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    status: ConversionHubJobStatus
    error: str | None = None
    result_artifact: DocumentConverterResultArtifact | None = None


class SaveDocumentConverterArtifactResult(BaseModel):
    """Return the Mina filer record created from the converted document."""

    model_config = ConfigDict(frozen=True)

    vault_artifact: ConversionHubSavedVaultArtifact
    source_artifact_id: str


def list_document_converter_routes() -> ConversionHubListRoutesResult:
    """Return the document/presentation route catalog for the MVP."""
    return ConversionHubListRoutesResult(routes=list(_DOCUMENT_ROUTES))


def validate_document_converter_route(spec: ConversionHubJobSpecV2) -> None:
    """Reject Conversion Hub specs outside the Document Converter MVP route set."""
    route = (spec.source_format, spec.output_format)
    if route not in _DOCUMENT_ROUTE_PAIRS:
        route_str = f"{spec.source_format.value} -> {spec.output_format.value}"
        raise validation_error(f"Unsupported Document Converter route: {route_str}")


def validate_document_converter_upload(
    *,
    spec: ConversionHubJobSpecV2,
    filename: str | None,
    content_type: str | None,
) -> tuple[str, str]:
    """Validate one upload against the declared Document Converter source format."""
    normalized_filename = (filename or "").strip()
    if not normalized_filename:
        raise validation_error("Uploaded file is missing a filename.")

    normalized_content_type = (content_type or "application/octet-stream").strip().lower()
    allowed_suffixes = _SOURCE_UPLOAD_SUFFIXES[spec.source_format]
    allowed_content_types = _SOURCE_UPLOAD_CONTENT_TYPES[spec.source_format]

    lower_filename = normalized_filename.lower()
    if not any(lower_filename.endswith(suffix) for suffix in allowed_suffixes):
        raise validation_error(
            "Document Converter filename does not match the selected source format.",
            details={
                "source_format": spec.source_format.value,
                "filename": normalized_filename,
                "allowed_file_suffixes": sorted(allowed_suffixes),
            },
        )

    if (
        normalized_content_type not in allowed_content_types
        and normalized_content_type not in _GENERIC_UPLOAD_CONTENT_TYPES
    ):
        raise validation_error(
            "Document Converter content type does not match the selected source format.",
            details={
                "source_format": spec.source_format.value,
                "content_type": normalized_content_type,
                "allowed_content_types": sorted(allowed_content_types),
            },
        )

    return normalized_filename, normalized_content_type or "application/octet-stream"


def validate_document_converter_batch_count(*, files_count: int) -> None:
    """Validate the first general Document Converter batch item count."""
    if files_count < 1:
        raise validation_error("At least one Document Converter item is required.")
    if files_count > DOCUMENT_CONVERTER_MAX_BATCH_ITEMS:
        raise validation_error(
            "Document Converter accepts at most 10 input items per batch.",
            details={
                "max_items": DOCUMENT_CONVERTER_MAX_BATCH_ITEMS,
                "items": files_count,
            },
        )


def is_document_converter_job(job: ConversionHubJob) -> bool:
    """Return true when a local Conversion Hub job belongs to Document Converter."""
    return (job.source_format, job.output_format) in _DOCUMENT_ROUTE_PAIRS


def is_local_document_converter_job(job: ConversionHubJob) -> bool:
    """Return true when a Document Converter job was produced locally."""
    upstream_id = job.upstream_job_id or ""
    return upstream_id.startswith(LOCAL_DOCUMENT_CONVERTER_PRODUCER_PREFIX)


def build_local_document_converter_producer_id(*, job_id: UUID) -> str:
    """Build the local producer identity stored on the existing job ledger."""
    return f"{LOCAL_DOCUMENT_CONVERTER_PRODUCER_PREFIX}{job_id}"


def build_document_converter_source_artifact_id(*, upstream_job_id: str) -> str:
    """Build the stable Vault source artifact id for the single MVP artifact."""
    return f"document-converter:{upstream_job_id}:{DOCUMENT_CONVERTER_ARTIFACT_KEY}"


def build_document_converter_result_artifact(
    *, job: ConversionHubJob
) -> DocumentConverterResultArtifact | None:
    """Build a modest result summary once a document conversion has succeeded."""
    if job.status is not ConversionHubJobStatus.SUCCEEDED or job.upstream_job_id is None:
        return None
    return DocumentConverterResultArtifact(
        filename=_default_result_filename(job=job),
        content_type=_OUTPUT_CONTENT_TYPES.get(job.output_format),
        size_bytes=None,
        sha256=None,
        source_artifact_id=build_document_converter_source_artifact_id(
            upstream_job_id=job.upstream_job_id
        ),
    )


def _default_result_filename(*, job: ConversionHubJob) -> str:
    safe_input = sanitize_input_filename(input_filename=job.input_filename)
    return build_document_converter_result_filename(
        input_filename=safe_input,
        output_format=job.output_format,
    )


def build_document_converter_result_filename(
    *,
    input_filename: str,
    output_format: ConversionHubOutputFormatV2,
) -> str:
    """Build the default output filename for one converted document."""
    safe_input = sanitize_input_filename(input_filename=input_filename)
    extension = _OUTPUT_EXTENSIONS[output_format]
    stem = PurePosixPath(safe_input).stem or "converted"
    return f"{stem}.{extension}"


def get_document_converter_output_content_type(
    output_format: ConversionHubOutputFormatV2,
) -> str | None:
    """Return the default content type for one Document Converter output."""
    return _OUTPUT_CONTENT_TYPES.get(output_format)
