from __future__ import annotations

import shutil
import tarfile
from collections.abc import Iterable, Iterator
from io import RawIOBase
from pathlib import Path
from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.infrastructure.artifacts.filesystem import build_artifacts_manifest
from skriptoteket.infrastructure.runner.path_safety import validate_output_path
from skriptoteket.protocols.runner import ArtifactManagerProtocol

_TAR_READ_CHUNK_BYTES = 1024 * 64


class _IterableReader(RawIOBase):
    def __init__(self, data: Iterable[bytes]) -> None:
        self._iterator: Iterator[bytes] = iter(data)
        self._buffer = b""

    def readable(self) -> bool:  # noqa: D102
        return True

    def read(self, size: int = -1) -> bytes:  # noqa: D102
        if size == 0:
            return b""
        if size < 0:
            chunks = [self._buffer]
            self._buffer = b""
            chunks.extend(self._iterator)
            return b"".join(chunks)

        while len(self._buffer) < size:
            try:
                self._buffer += next(self._iterator)
            except StopIteration:
                break

        result = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return result


def _safe_extract_tar(
    *,
    tar_stream: Iterable[bytes],
    destination_dir: Path,
) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_root = destination_dir.resolve()

    with tarfile.open(fileobj=_IterableReader(tar_stream), mode="r|*") as tar:
        for member in tar:
            if member.name in {"", "."}:
                continue

            relative_path = validate_output_path(path=member.name)
            target_path = (destination_dir / relative_path).resolve()
            if destination_root not in target_path.parents and destination_root != target_path:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: unsafe artifact path",
                    details={"path": member.name},
                )

            if member.isdir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            if not member.isreg():
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: unsupported artifact type",
                    details={"path": member.name, "type": member.type},
                )

            extracted = tar.extractfile(member)
            if extracted is None:
                raise DomainError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Runner contract violation: failed to read artifact content",
                    details={"path": member.name},
                )

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open("wb") as out_file:
                with extracted:
                    shutil.copyfileobj(extracted, out_file, length=_TAR_READ_CHUNK_BYTES)


class FilesystemArtifactManager(ArtifactManagerProtocol):
    def __init__(self, *, artifacts_root: Path) -> None:
        self._artifacts_root = artifacts_root

    def store_output_archive(
        self,
        *,
        run_id: UUID,
        output_archive: Iterable[bytes],
        reported_artifacts: list[RunnerArtifact],
    ) -> ArtifactsManifest:
        for artifact in reported_artifacts:
            validate_output_path(path=artifact.path)

        run_dir = self._artifacts_root / str(run_id)
        if run_dir.exists():
            return build_artifacts_manifest(run_dir=run_dir)
        run_dir.mkdir(parents=True, exist_ok=False)

        _safe_extract_tar(tar_stream=output_archive, destination_dir=run_dir)
        return build_artifacts_manifest(run_dir=run_dir)
