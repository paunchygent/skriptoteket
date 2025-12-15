import io
import tarfile
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.execution import RunnerArtifact
from skriptoteket.infrastructure.runner.artifact_manager import FilesystemArtifactManager


def _build_tar_bytes(*, members: list[tuple[str, bytes]]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for name, data in members:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return tar_buffer.getvalue()


def test_store_output_archive_extracts_and_builds_manifest(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    tar_bytes = _build_tar_bytes(members=[("output/report.txt", b"hello")])
    manifest = manager.store_output_archive(
        run_id=run_id,
        output_archive=[tar_bytes],
        reported_artifacts=[RunnerArtifact(path="output/report.txt", bytes=5)],
    )

    stored_path = tmp_path / str(run_id) / "output" / "report.txt"
    assert stored_path.read_bytes() == b"hello"
    assert manifest.artifacts[0].path == "output/report.txt"


def test_store_output_archive_rejects_path_traversal(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    tar_bytes = _build_tar_bytes(members=[("../evil.txt", b"nope")])
    with pytest.raises(DomainError) as exc_info:
        manager.store_output_archive(
            run_id=run_id,
            output_archive=[tar_bytes],
            reported_artifacts=[],
        )
    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
