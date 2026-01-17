from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .protocols import (
    DockerClientProtocol,
    DockerContainerProtocol,
    DockerContainersClientProtocol,
    DockerVolumeProtocol,
    DockerVolumesClientProtocol,
)


class DockerVolumeAdapter(DockerVolumeProtocol):
    def __init__(self, volume: Any) -> None:
        self._volume = volume

    @property
    def name(self) -> str:
        return str(self._volume.name)

    def remove(self, *, force: bool) -> None:
        self._volume.remove(force=force)


class DockerContainerAdapter(DockerContainerProtocol):
    def __init__(self, container: Any) -> None:
        self._container = container

    def put_archive(self, *, path: str, data: bytes) -> bool:
        return bool(self._container.put_archive(path=path, data=data))

    def start(self) -> None:
        self._container.start()

    def wait(self, *, timeout: int) -> object:
        return self._container.wait(timeout=timeout)

    def kill(self) -> None:
        self._container.kill()

    def logs(self, *, stdout: bool, stderr: bool) -> bytes:
        return bytes(self._container.logs(stdout=stdout, stderr=stderr))

    def get_archive(self, *, path: str) -> tuple[Iterable[bytes], object]:
        stream_any, stat_any = self._container.get_archive(path=path)
        stream: Iterable[bytes] = (bytes(chunk) for chunk in stream_any)
        stat: object = stat_any
        return stream, stat

    def remove(self, *, force: bool) -> None:
        self._container.remove(force=force)


class DockerVolumesClientAdapter(DockerVolumesClientProtocol):
    def __init__(self, volumes: Any) -> None:
        self._volumes = volumes

    def create(self, **kwargs: object) -> DockerVolumeProtocol:
        return DockerVolumeAdapter(self._volumes.create(**kwargs))


class DockerContainersClientAdapter(DockerContainersClientProtocol):
    def __init__(self, containers: Any) -> None:
        self._containers = containers

    def create(self, **kwargs: object) -> DockerContainerProtocol:
        return DockerContainerAdapter(self._containers.create(**kwargs))


class DockerClientAdapter(DockerClientProtocol):
    def __init__(self, client: Any) -> None:
        self._client = client
        self._containers = DockerContainersClientAdapter(client.containers)
        self._volumes = DockerVolumesClientAdapter(client.volumes)

    @property
    def containers(self) -> DockerContainersClientProtocol:
        return self._containers

    @property
    def volumes(self) -> DockerVolumesClientProtocol:
        return self._volumes

    def close(self) -> None:
        self._client.close()
