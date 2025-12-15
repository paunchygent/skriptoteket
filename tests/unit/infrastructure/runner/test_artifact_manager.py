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


def test_store_output_archive_with_empty_output_returns_empty_manifest(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    tar_bytes = _build_tar_bytes(members=[])
    manifest = manager.store_output_archive(
        run_id=run_id,
        output_archive=[tar_bytes],
        reported_artifacts=[],
    )

    assert manifest.artifacts == []


def test_store_output_archive_deduplicates_artifact_ids(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    # Two files in different subdirs that would produce similar slugified artifact_ids
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        # Add output/sub1 dir
        dir1_info = tarfile.TarInfo(name="output/sub1")
        dir1_info.type = tarfile.DIRTYPE
        tar.addfile(dir1_info)

        # Add output/sub2 dir
        dir2_info = tarfile.TarInfo(name="output/sub2")
        dir2_info.type = tarfile.DIRTYPE
        tar.addfile(dir2_info)

        # Two files that slug to similar IDs
        data1 = b"file1"
        info1 = tarfile.TarInfo(name="output/sub1/report.txt")
        info1.size = len(data1)
        tar.addfile(info1, io.BytesIO(data1))

        data2 = b"file2"
        info2 = tarfile.TarInfo(name="output/sub2/report.txt")
        info2.size = len(data2)
        tar.addfile(info2, io.BytesIO(data2))

    manifest = manager.store_output_archive(
        run_id=run_id,
        output_archive=[tar_buffer.getvalue()],
        reported_artifacts=[],
    )

    artifact_ids = [a.artifact_id for a in manifest.artifacts]
    assert len(artifact_ids) == 2
    assert len(set(artifact_ids)) == 2  # All unique


def test_store_output_archive_with_nested_directories(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        # Add directory entry
        dir_info = tarfile.TarInfo(name="output/subdir")
        dir_info.type = tarfile.DIRTYPE
        tar.addfile(dir_info)

        # Add file in nested directory
        data = b"nested content"
        info = tarfile.TarInfo(name="output/subdir/file.txt")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    manifest = manager.store_output_archive(
        run_id=run_id,
        output_archive=[tar_buffer.getvalue()],
        reported_artifacts=[],
    )

    stored_path = tmp_path / str(run_id) / "output" / "subdir" / "file.txt"
    assert stored_path.read_bytes() == b"nested content"
    assert len(manifest.artifacts) == 1


def test_store_output_archive_rejects_reported_artifact_with_invalid_path(tmp_path) -> None:
    run_id = uuid4()
    manager = FilesystemArtifactManager(artifacts_root=tmp_path)

    tar_bytes = _build_tar_bytes(members=[("output/valid.txt", b"ok")])
    with pytest.raises(DomainError) as exc_info:
        manager.store_output_archive(
            run_id=run_id,
            output_archive=[tar_bytes],
            reported_artifacts=[RunnerArtifact(path="../evil.txt", bytes=5)],
        )

    assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
