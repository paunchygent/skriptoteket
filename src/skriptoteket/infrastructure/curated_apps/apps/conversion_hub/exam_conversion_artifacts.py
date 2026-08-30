"""Filesystem storage for in-process Exam Converter artifacts.

Purpose:
    Persist server-owned in-process Exam Converter bundles under the existing
    Skriptoteket artifacts root so downloads use the local job id as authority
    inside the Skriptoteket application boundary.

Relationships:
    Implements ``ExamConversionArtifactStoreProtocol`` for
    ``CreateExamConverterConversionJobsHandler`` and the Conversion Hub
    artifact download handler.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.protocols.exam_conversion import ExamConversionArtifactStoreProtocol

_CONTENT_FILENAME = "examnet_bundle.zip"
_METADATA_FILENAME = "examnet_bundle.json"
_SOURCE_FILENAME = "source.dxe"
_NAMED_DIRECTORY = "named"
_GENERATIONS_DIRECTORY = "generations"
_CURRENT_FILENAME = "current.json"


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
        generation_id = str(uuid4())
        generation_dir = job_dir / _GENERATIONS_DIRECTORY / generation_id
        generation_dir.mkdir(parents=True, exist_ok=False)
        _atomic_write_bytes(path=generation_dir / _CONTENT_FILENAME, content=artifact.content)
        _atomic_write_bytes(path=generation_dir / _SOURCE_FILENAME, content=artifact.source_content)
        named_dir = generation_dir / _NAMED_DIRECTORY
        named_dir.mkdir(parents=True, exist_ok=True)
        for named in artifact.named_artifacts:
            _atomic_write_bytes(path=named_dir / named.artifact_key, content=named.content)
        _atomic_write_text(
            path=generation_dir / _METADATA_FILENAME,
            content=json.dumps(
                {
                    "filename": artifact.filename,
                    "content_type": artifact.content_type,
                    "source_filename": artifact.source_filename,
                    "named_artifacts": [
                        {
                            "artifact_key": named.artifact_key,
                            "filename": named.filename,
                            "content_type": named.content_type,
                        }
                        for named in artifact.named_artifacts
                    ],
                },
                sort_keys=True,
            ),
        )
        _atomic_write_text(
            path=job_dir / _CURRENT_FILENAME,
            content=json.dumps({"generation_id": generation_id}, sort_keys=True),
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
        job_dir = self._current_generation_dir(job_id=job_id)
        metadata_path = job_dir / _METADATA_FILENAME
        content_path = job_dir / _CONTENT_FILENAME
        source_path = job_dir / _SOURCE_FILENAME
        if not metadata_path.is_file() or not content_path.is_file() or not source_path.is_file():
            raise not_found("ExamConversionArtifact", str(job_id))

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise validation_error("Exam Converter artifact metadata is invalid.") from exc

        raw_named_artifacts = metadata.get("named_artifacts", [])
        if not isinstance(raw_named_artifacts, list):
            raise validation_error("Exam Converter named artifact metadata is invalid.")
        named_artifacts = tuple(
            self._read_named_from_metadata(job_dir=job_dir, entry=entry)
            for entry in raw_named_artifacts
            if isinstance(entry, dict)
        )
        return ExamConversionStoredArtifact(
            filename=str(metadata.get("filename") or ""),
            content_type=str(metadata.get("content_type") or ""),
            content=content_path.read_bytes(),
            source_filename=str(metadata.get("source_filename") or ""),
            source_content=source_path.read_bytes(),
            named_artifacts=named_artifacts,
        )

    def read_named_artifact(
        self,
        *,
        job_id: UUID,
        artifact_key: str,
    ) -> ExamConversionNamedArtifact:
        """Read one named product artifact by its stable key."""

        artifact = self.read_artifact(job_id=job_id)
        for named in artifact.named_artifacts:
            if named.artifact_key == artifact_key:
                return named
        raise not_found("ExamConversionNamedArtifact", f"{job_id}:{artifact_key}")

    def _read_named_from_metadata(
        self,
        *,
        job_dir: Path,
        entry: dict[str, JsonValue],
    ) -> ExamConversionNamedArtifact:
        artifact_key = str(entry.get("artifact_key") or "")
        if not artifact_key or not artifact_key.replace("_", "").isalnum():
            raise validation_error("Exam Converter named artifact metadata is invalid.")
        content_path = job_dir / _NAMED_DIRECTORY / artifact_key
        if not content_path.is_file():
            raise not_found("ExamConversionNamedArtifact", artifact_key)
        return ExamConversionNamedArtifact(
            artifact_key=artifact_key,
            filename=str(entry.get("filename") or ""),
            content_type=str(entry.get("content_type") or ""),
            content=content_path.read_bytes(),
        )

    def _job_dir(self, *, job_id: UUID) -> Path:
        candidate = (self._root / str(job_id)).resolve()
        root = self._root.resolve()
        if root not in candidate.parents and root != candidate:
            raise validation_error("Exam Converter artifact path is invalid.")
        return candidate

    def _current_generation_dir(self, *, job_id: UUID) -> Path:
        job_dir = self._job_dir(job_id=job_id)
        pointer_path = job_dir / _CURRENT_FILENAME
        if not pointer_path.is_file():
            raise not_found("ExamConversionArtifact", str(job_id))
        try:
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise validation_error("Exam Converter artifact pointer is invalid.") from exc
        generation_id = pointer.get("generation_id")
        if not isinstance(generation_id, str):
            raise validation_error("Exam Converter artifact pointer is invalid.")
        generation_dir = (job_dir / _GENERATIONS_DIRECTORY / generation_id).resolve()
        generations_root = (job_dir / _GENERATIONS_DIRECTORY).resolve()
        if generations_root not in generation_dir.parents:
            raise validation_error("Exam Converter artifact pointer is invalid.")
        return generation_dir


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
