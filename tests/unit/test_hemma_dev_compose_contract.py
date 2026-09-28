"""Rendered Skriptoteket Hemma staging compose and Vite unit coherence.

Purpose:
    Render `compose.hemma-dev.yaml` with Docker Compose and prove the outcomes
    staging depends on: loopback-only publishing, reachability from the HuleEdu
    staging Gateway, runner access through the rootless daemon, isolation from
    the Gateway private key, and agreement with the paths and guards that
    `scripts/hemma_dev.py` and the fixture command use.

Relationships:
    - Renders `compose.hemma-dev.yaml`; reads `systemd/skriptoteket-vite-dev.service`.
    - `scripts/hemma_dev.py` drives both on Hemma; the real start is phase-2 proof.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

import pytest

from scripts import hemma_dev
from skriptoteket.cli.commands.setup_staging_proof_fixture import require_staging_target
from skriptoteket.config import Settings

ROOT = Path(__file__).resolve().parents[2]
SECRETS_ROOT = PurePosixPath("/home/paunchygent/apps/huleedu-dev/secrets")


@pytest.fixture(scope="module")
def rendered() -> dict[str, Any]:
    if shutil.which("docker") is None:
        pytest.skip("docker CLI is not installed")
    environment = hemma_dev.staging_environment(os.environ)
    environment["SKRIPTOTEKET_DEV_DB_PASSWORD"] = "render-only"
    completed = subprocess.run(
        [*hemma_dev.COMPOSE, "--profile", "build-only", "config", "--format", "json"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    config: dict[str, Any] = json.loads(completed.stdout)
    return config


def _environment(service: dict[str, Any]) -> dict[str, str]:
    return {key: str(value) for key, value in service["environment"].items()}


def test_only_web_is_published_and_only_on_loopback(rendered: dict[str, Any]) -> None:
    published = {name: service.get("ports", []) for name, service in rendered["services"].items()}

    assert [name for name, ports in published.items() if ports] == ["web"]
    assert {(port["host_ip"], port["published"]) for port in published["web"]} == {
        ("127.0.0.1", "18000")
    }


def test_huleedu_gateway_reaches_web_as_skriptoteket_web(rendered: dict[str, Any]) -> None:
    web_networks = rendered["services"]["web"]["networks"]
    external = {
        key: network
        for key, network in rendered["networks"].items()
        if network.get("external") and network["name"] == hemma_dev.HULEEDU_NETWORK
    }

    assert len(external) == 1
    (network_key,) = external
    assert "skriptoteket-web" in web_networks[network_key]["aliases"]


def test_web_and_worker_reach_the_rootless_daemon_and_the_built_runner(
    rendered: dict[str, Any],
) -> None:
    runner_image = rendered["services"]["runner"]["image"]
    socket_path = hemma_dev.ROOTLESS_DOCKER_HOST.removeprefix("unix://")

    for name in ("web", "worker"):
        service = rendered["services"][name]
        environment = _environment(service)
        bind_targets = {
            volume["target"] for volume in service["volumes"] if volume["type"] == "bind"
        }
        assert environment["DOCKER_HOST"] == hemma_dev.ROOTLESS_DOCKER_HOST
        assert socket_path in bind_targets
        assert environment["RUNNER_IMAGE"] == runner_image


def test_web_and_worker_share_artifact_and_vault_storage(rendered: dict[str, Any]) -> None:
    def storage(name: str) -> set[tuple[str, str]]:
        service = rendered["services"][name]
        environment = _environment(service)
        mounted = {volume["target"]: volume["source"] for volume in service["volumes"]}
        return {
            (environment[key], mounted[environment[key]])
            for key in ("ARTIFACTS_ROOT", "VAULT_ROOT")
        }

    assert storage("web") == storage("worker")


def test_only_the_gateway_public_key_is_mounted_from_huleedu_secrets(
    rendered: dict[str, Any],
) -> None:
    secret_binds = [
        (name, volume)
        for name, service in rendered["services"].items()
        for volume in service.get("volumes", [])
        if volume["type"] == "bind" and PurePosixPath(volume["source"]).is_relative_to(SECRETS_ROOT)
    ]
    web_environment = _environment(rendered["services"]["web"])

    assert len(secret_binds) == 1
    name, volume = secret_binds[0]
    assert name == "web"
    assert volume["source"] == str(hemma_dev.IDENTITY_PUBLIC_KEY_HOST_PATH)
    assert volume["read_only"] is True
    assert volume["target"] == web_environment["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"]


def test_lifecycle_export_path_resolves_to_the_preflighted_host_file(
    rendered: dict[str, Any],
) -> None:
    container_path = PurePosixPath(hemma_dev.PROOF_EXPORT_CONTAINER_PATH)
    (mount,) = [
        volume
        for volume in rendered["services"]["web"]["volumes"]
        if volume["type"] == "bind"
        and container_path.is_relative_to(PurePosixPath(volume["target"]))
    ]

    host_path = PurePosixPath(mount["source"]) / container_path.relative_to(mount["target"])
    assert host_path == PurePosixPath(hemma_dev.PROOF_EXPORT_HOST_PATH)
    assert mount["read_only"] is True


def test_rendered_web_settings_pass_the_fixture_staging_guard(rendered: dict[str, Any]) -> None:
    environment = _environment(rendered["services"]["web"])

    require_staging_target(
        Settings(
            ENVIRONMENT=environment["ENVIRONMENT"],
            DATABASE_URL=environment["DATABASE_URL"],
        )
    )


def test_vite_unit_serves_the_checkout_frontend_and_proxies_to_published_web(
    rendered: dict[str, Any],
) -> None:
    unit_text = (ROOT / hemma_dev.VITE_UNIT_SOURCE).read_text(encoding="utf-8")
    settings = dict(line.split("=", 1) for line in unit_text.splitlines() if "=" in line)
    environment = dict(
        line.removeprefix("Environment=").split("=", 1)
        for line in unit_text.splitlines()
        if line.startswith("Environment=")
    )
    (web_port,) = rendered["services"]["web"]["ports"]
    backend = urlsplit(environment["VITE_DEV_BACKEND_PROXY_TARGET"])

    assert Path(settings["WorkingDirectory"]) == hemma_dev.STAGING_CHECKOUT / "frontend"
    assert environment["VITE_DEV_PORT"] == str(urlsplit(hemma_dev.VITE_URL).port)
    assert (backend.hostname, str(backend.port)) == (web_port["host_ip"], web_port["published"])
