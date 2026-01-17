from __future__ import annotations

import os
from typing import NoReturn

from docker.errors import DockerException

from skriptoteket.domain.errors import DomainError, ErrorCode


def raise_docker_client_unavailable(*, exc: DockerException) -> NoReturn:
    docker_host = os.environ.get("DOCKER_HOST")
    docker_sock_present = os.path.exists("/var/run/docker.sock")
    if not docker_host and not docker_sock_present:
        raise DomainError(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=(
                "Tool execution is unavailable: Docker socket /var/run/docker.sock is not "
                "mounted. Start dev with: `pdm run dev-start` "
                "(uses compose.dev.yaml)."
            ),
            details={
                "reason": "docker_sock_missing",
                "docker_sock_path": "/var/run/docker.sock",
            },
        ) from exc

    raise DomainError(
        code=ErrorCode.SERVICE_UNAVAILABLE,
        message=(
            "Tool execution is unavailable: Docker is not reachable. Ensure the service "
            "has access to Docker (socket/DOCKER_HOST) and that Docker is running."
        ),
        details={
            "reason": "docker_unreachable",
        },
    ) from exc
