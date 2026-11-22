from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class DockerContainerProtocol(Protocol):
    @property
    def status(self) -> str: ...

    def reload(self) -> None: ...

    def put_archive(self, *, path: str, data: bytes) -> bool: ...

    def start(self) -> None: ...

    def wait(self, *, timeout: int) -> object: ...

    def kill(self) -> None: ...

    def logs(self, *, stdout: bool, stderr: bool) -> bytes: ...

    def get_archive(self, *, path: str) -> tuple[Iterable[bytes], object]: ...

    def remove(self, *, force: bool) -> None: ...


class DockerVolumeProtocol(Protocol):
    @property
    def name(self) -> str: ...

    def remove(self, *, force: bool) -> None: ...


class DockerVolumesClientProtocol(Protocol):
    def create(self, *, labels: dict[str, str]) -> DockerVolumeProtocol: ...

    def list(self, *, filters: dict[str, str | list[str] | bool]) -> list[DockerVolumeProtocol]: ...


class DockerContainersClientProtocol(Protocol):
    def create(
        self,
        *,
        image: str,
        environment: dict[str, str],
        command: list[str],
        working_dir: str,
        network_mode: str,
        user: str,
        cap_drop: list[str],
        pids_limit: int,
        read_only: bool,
        tmpfs: dict[str, str],
        volumes: dict[str, dict[str, str]],
        mem_limit: str,
        nano_cpus: int,
        labels: dict[str, str],
    ) -> DockerContainerProtocol: ...

    def list(
        self, *, all: bool, filters: dict[str, str | list[str] | bool]
    ) -> list[DockerContainerProtocol]: ...


class DockerClientProtocol(Protocol):
    @property
    def volumes(self) -> DockerVolumesClientProtocol: ...

    @property
    def containers(self) -> DockerContainersClientProtocol: ...

    def close(self) -> None: ...
