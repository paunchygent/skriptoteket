"""Filesystem storage for in-process Exam Converter artifacts.

Purpose:
    Persist server-owned in-process Exam Converter bundles under the existing
    Skriptoteket artifacts root so downloads use the local job id as authority
    instead of upstream Sir Convert artifact references.

Relationships:
    Implements ``ExamConversionArtifactStoreProtocol`` for
    ``CreateExamConverterConversionJobsHandler`` and the Conversion Hub
    artifact download handler.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol

_CONTENT_FILENAME = "examnet_bundle.zip"
_METADATA_FILENAME = "examnet_bundle.json"


class FilesystemExamConversionArtifactStore(ExamConversionArtifactStoreProtocol):
    """Store in-process Exam Converter bundle bytes on the server filesystem."""

    def __init__(self, *, artifacts_root: Path) -> None:
        self._root = artifacts_root / "exam-conversion"

    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: ExamConversionStoredArtifact,
    ) -> None:
        """Store one bundle artifact for a local Exam Converter job.

        Args:
            job_id: Owner-scoped local Conversion Hub job id.
            artifact: Produced bundle metadata and bytes.
        """
        job_dir = self._job_dir(job_id=job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_bytes(path=job_dir / _CONTENT_FILENAME, content=artifact.content)
        _atomic_write_text(
            path=job_dir / _METADATA_FILENAME,
            content=json.dumps(
                {
                    "filename": artifact.filename,
                    "content_type": artifact.content_type,
                },
                sort_keys=True,
            ),
        )

    def read_artifact(self, *, job_id: UUID) -> ExamConversionStoredArtifact:
        """Read the bundle artifact for a local Exam Converter job.

        Args:
            job_id: Owner-scoped local Conversion Hub job id.

        Returns:
            The stored bundle payload.

        Raises:
            DomainError: If the artifact metadata or bytes are missing.
        """
        job_dir = self._job_dir(job_id=job_id)
        metadata_path = job_dir / _METADATA_FILENAME
        content_path = job_dir / _CONTENT_FILENAME
        if not metadata_path.is_file() or not content_path.is_file():
            raise not_found("ExamConversionArtifact", str(job_id))

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise validation_error("Exam Converter artifact metadata is invalid.") from exc

        return ExamConversionStoredArtifact(
            filename=str(metadata.get("filename") or ""),
            content_type=str(metadata.get("content_type") or ""),
            content=content_path.read_bytes(),
        )

    def _job_dir(self, *, job_id: UUID) -> Path:
        candidate = (self._root / str(job_id)).resolve()
        root = self._root.resolve()
        if root not in candidate.parents and root != candidate:
            raise validation_error("Exam Converter artifact path is invalid.")
        return candidate


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
