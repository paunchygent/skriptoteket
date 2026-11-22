from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from .protocols import (
    DockerClientProtocol,
    DockerContainerProtocol,
    DockerContainersClientProtocol,
    DockerVolumeProtocol,
    DockerVolumesClientProtocol,
)

if TYPE_CHECKING:
    from docker import DockerClient
    from docker.models.containers import Container, ContainerCollection
    from docker.models.volumes import Volume, VolumeCollection


class DockerVolumeAdapter(DockerVolumeProtocol):
    def __init__(self, volume: Volume) -> None:
        self._volume = volume

    @property
    def name(self) -> str:
        return str(self._volume.name)

    def remove(self, *, force: bool) -> None:
        self._volume.remove(force=force)


class DockerContainerAdapter(DockerContainerProtocol):
    def __init__(self, container: Container) -> None:
        self._container = container

    @property
    def status(self) -> str:
        return str(self._container.status)

    def reload(self) -> None:
        self._container.reload()

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
    def __init__(self, volumes: VolumeCollection) -> None:
        self._volumes = volumes

    def create(self, **kwargs: object) -> DockerVolumeProtocol:
        create_volume: Callable[..., Volume] = self._volumes.create
        return DockerVolumeAdapter(create_volume(**kwargs))

    def list(self, **kwargs: object) -> list[DockerVolumeProtocol]:
        list_volumes: Callable[..., list[Volume]] = self._volumes.list
        return [DockerVolumeAdapter(volume) for volume in list_volumes(**kwargs)]


class DockerContainersClientAdapter(DockerContainersClientProtocol):
    def __init__(self, containers: ContainerCollection) -> None:
        self._containers = containers

    def create(self, **kwargs: object) -> DockerContainerProtocol:
        create_container: Callable[..., Container] = self._containers.create
        return DockerContainerAdapter(create_container(**kwargs))

    def get(self, *args: object, **kwargs: object) -> DockerContainerProtocol:
        get_container: Callable[..., Container] = self._containers.get
        return DockerContainerAdapter(get_container(*args, **kwargs))

    def list(self, **kwargs: object) -> list[DockerContainerProtocol]:
        list_containers: Callable[..., list[Container]] = self._containers.list
        return [DockerContainerAdapter(container) for container in list_containers(**kwargs)]


class DockerClientAdapter(DockerClientProtocol):
    def __init__(self, client: DockerClient) -> None:
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
