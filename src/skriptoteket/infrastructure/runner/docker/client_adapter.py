from __future__ import annotations

from collections.abc import Iterable
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

    def create(self, *, labels: dict[str, str]) -> DockerVolumeProtocol:
        return DockerVolumeAdapter(self._volumes.create(labels=labels))

    def list(self, *, filters: dict[str, str | list[str] | bool]) -> list[DockerVolumeProtocol]:
        return [DockerVolumeAdapter(volume) for volume in self._volumes.list(filters=filters)]


class DockerContainersClientAdapter(DockerContainersClientProtocol):
    def __init__(self, containers: ContainerCollection) -> None:
        self._containers = containers

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
    ) -> DockerContainerProtocol:
        return DockerContainerAdapter(
            self._containers.create(
                image=image,
                environment=environment,
                command=command,
                working_dir=working_dir,
                network_mode=network_mode,
                user=user,
                cap_drop=cap_drop,
                pids_limit=pids_limit,
                read_only=read_only,
                tmpfs=tmpfs,
                volumes=volumes,
                mem_limit=mem_limit,
                nano_cpus=nano_cpus,
                labels=labels,
            )
        )

    def list(
        self, *, all: bool, filters: dict[str, str | list[str] | bool]
    ) -> list[DockerContainerProtocol]:
        return [
            DockerContainerAdapter(container)
            for container in self._containers.list(all=all, filters=filters)
        ]


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
