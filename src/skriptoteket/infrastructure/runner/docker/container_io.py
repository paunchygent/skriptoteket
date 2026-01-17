from __future__ import annotations

import io
import tarfile
from uuid import UUID

from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.protocols.runner import ArtifactManagerProtocol

from .protocols import DockerContainerProtocol


def truncate_utf8_bytes(*, data: bytes, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    if len(data) <= max_bytes:
        return data.decode("utf-8", errors="replace")
    return data[:max_bytes].decode("utf-8", errors="replace")


def truncate_utf8_str(*, value: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def extract_first_file_from_tar_bytes(*, tar_bytes: bytes) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:*") as tar:
        for member in tar:
            if not member.isreg():
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            with extracted:
                return extracted.read()
    raise RuntimeError("No file found in tar archive")


def fetch_stdout_stderr(
    *,
    container: DockerContainerProtocol,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[str, str]:
    stdout_raw = container.logs(stdout=True, stderr=False)
    stderr_raw = container.logs(stdout=False, stderr=True)
    stdout = truncate_utf8_bytes(data=stdout_raw, max_bytes=max_stdout_bytes)
    stderr = truncate_utf8_bytes(data=stderr_raw, max_bytes=max_stderr_bytes)
    return stdout, stderr


def fetch_result_json_bytes(*, container: DockerContainerProtocol) -> bytes | None:
    from docker.errors import DockerException, NotFound

    try:
        tar_stream, _ = container.get_archive(path="/work/result.json")
        return extract_first_file_from_tar_bytes(tar_bytes=b"".join(tar_stream))
    except (NotFound, DockerException, RuntimeError):
        return None


def store_output_archive(
    *,
    container: DockerContainerProtocol,
    run_id: UUID,
    reported_artifacts: list[RunnerArtifact],
    artifacts: ArtifactManagerProtocol,
) -> ArtifactsManifest:
    from docker.errors import DockerException, NotFound

    try:
        tar_stream, _ = container.get_archive(path="/work/output")
        return artifacts.store_output_archive(
            run_id=run_id,
            output_archive=tar_stream,
            reported_artifacts=reported_artifacts,
        )
    except (NotFound, DockerException):
        return ArtifactsManifest(artifacts=[])


def store_output_archive_safely(
    *,
    container: DockerContainerProtocol,
    run_id: UUID,
    artifacts: ArtifactManagerProtocol,
) -> ArtifactsManifest:
    try:
        return store_output_archive(
            container=container,
            run_id=run_id,
            reported_artifacts=[],
            artifacts=artifacts,
        )
    except DomainError:
        return ArtifactsManifest(artifacts=[])
