"""Public Exam Converter artifact projection helpers.

Purpose:
  Project browser-safe artifact metadata for the public Exam Converter lane.

Relationships:
  - Used by `handlers.public_exam_converter_jobs`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from pydantic import JsonValue

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterArtifactEntry,
    PublicExamConverterArtifactManifestResponse,
    PublicExamConverterJobStatus,
    PublicExamConverterUpload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_schema_versions import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)


def upload_mime_types(
    *,
    source_dxe: PublicExamConverterUpload,
    graded_result_pdf: PublicExamConverterUpload | None,
) -> tuple[str, ...]:
    values = [source_dxe.content_type]
    if graded_result_pdf is not None:
        values.append(graded_result_pdf.content_type)
    normalized: list[str] = []
    for value in values:
        candidate = value.strip().lower()
        if candidate and candidate not in normalized:
            normalized.append(candidate)
    return tuple(normalized)


def project_public_exam_converter_manifest(
    *,
    public_job_id: str,
    status: PublicExamConverterJobStatus,
    expires_at: datetime,
    manifest: Mapping[str, JsonValue],
    api_namespace: str,
) -> PublicExamConverterArtifactManifestResponse:
    artifact_entries = manifest.get("artifacts")
    artifacts: list[PublicExamConverterArtifactEntry] = []
    if isinstance(artifact_entries, list):
        artifacts = [
            _project_artifact_entry(
                entry=entry,
                public_job_id=public_job_id,
                api_namespace=api_namespace,
            )
            for entry in artifact_entries
            if isinstance(entry, dict)
        ]
    return PublicExamConverterArtifactManifestResponse(
        schema_version=_string_value(manifest.get("schema_version"))
        or DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        public_job_id=public_job_id,
        status=status,
        expires_at=expires_at,
        bundle_status=_string_value(manifest.get("bundle_status")),
        artifacts=artifacts,
        manual_follow_up=_dict_value(manifest.get("manual_follow_up")),
        readiness=_dict_value(manifest.get("readiness")),
        source_binding=_dict_value(manifest.get("source_binding")),
        warnings=_dict_value(manifest.get("warnings")),
    )


def _project_artifact_entry(
    *,
    entry: Mapping[str, JsonValue],
    public_job_id: str,
    api_namespace: str,
) -> PublicExamConverterArtifactEntry:
    artifact_key = _string_value(entry.get("artifact_key")) or "unknown"
    availability = _string_value(entry.get("availability")) or "unknown"
    download_url = None
    if availability == "available":
        download_url = f"{api_namespace}/jobs/{public_job_id}/artifacts/{artifact_key}/download"
    return PublicExamConverterArtifactEntry(
        artifact_key=artifact_key,
        filename=_string_value(entry.get("filename")),
        content_type=_string_value(entry.get("content_type")),
        availability=availability,
        size_bytes=_int_value(entry.get("size_bytes")),
        sha256=_string_value(entry.get("sha256")),
        download_url=download_url,
        unavailable_code=_string_value(entry.get("unavailable_code")),
    )


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int_value(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _dict_value(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items() if isinstance(key, str)}
