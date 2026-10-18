from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from skriptoteket.application.curated_apps.exam_conversion import ExamConversionStoredArtifact
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_conversion_artifacts import (
    FilesystemExamConversionArtifactStore,
)


def test_artifact_store_deletes_expired_job_directory(tmp_path: Path) -> None:
    job_id = uuid4()
    artifacts = FilesystemExamConversionArtifactStore(artifacts_root=tmp_path)
    artifacts.store_artifact(
        job_id=job_id,
        artifact=ExamConversionStoredArtifact(
            filename="bundle.zip",
            content_type="application/zip",
            content=b"bundle",
            source_filename="exam.dxe",
            source_content=b"dxe",
        ),
    )

    artifacts.delete_artifact(job_id=job_id)

    assert not (tmp_path / "exam-conversion" / str(job_id)).exists()
