from uuid import UUID

from .protocols import DockerClientProtocol, DockerContainerProtocol, DockerVolumeProtocol


def remove_container(
    container: DockerContainerProtocol | None,
    *,
    swallow_all: bool,
) -> None:
    if container is None:
        return
    try:
        container.remove(force=True)
    except Exception as exc:  # noqa: BLE001
        if swallow_all:
            return
        from docker.errors import DockerException

        if isinstance(exc, DockerException):
            return
        raise


def remove_volume(
    volume: DockerVolumeProtocol | None,
    *,
    swallow_all: bool,
) -> None:
    if volume is None:
        return
    try:
        volume.remove(force=True)
    except Exception as exc:  # noqa: BLE001
        if swallow_all:
            return
        from docker.errors import DockerException

        if isinstance(exc, DockerException):
            return
        raise


def remove_run_volumes(*, client: DockerClientProtocol | None, run_id: UUID) -> None:
    if client is None:
        return
    try:
        volumes = client.volumes.list(filters={"label": f"skriptoteket.run_id={run_id}"})
    except Exception:  # noqa: BLE001
        return
    for volume in volumes:
        try:
            volume.remove(force=True)
        except Exception:  # noqa: BLE001
            pass


def close_client(client: DockerClientProtocol | None) -> None:
    if client is None:
        return
    try:
        client.close()
    except AttributeError:
        pass
