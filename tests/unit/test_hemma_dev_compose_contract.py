"""Skriptoteket Hemma staging compose and Vite unit contract.

Purpose:
    Keep the `skriptoteket-dev` staging project loopback-only, reachable by the
    HuleEdu staging Gateway as `skriptoteket-web`, on the rootless daemon, and
    wired to the runner image it builds.

Relationships:
    - Guards `compose.hemma-dev.yaml` and `systemd/skriptoteket-vite-dev.service`.
    - `scripts/hemma_dev.py` drives both on Hemma.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts import hemma_dev

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "compose.hemma-dev.yaml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]
ROOTLESS_SOCKET = "/run/user/1000/docker.sock"


def test_project_name_matches_lifecycle_command() -> None:
    assert COMPOSE["name"] == hemma_dev.COMPOSE_PROJECT


def test_only_web_publishes_and_only_on_loopback_18000() -> None:
    published = {name: service.get("ports", []) for name, service in SERVICES.items()}

    assert published["web"] == ["127.0.0.1:18000:8000"]
    assert all(not ports for name, ports in published.items() if name != "web")


def test_web_joins_huleedu_staging_network_as_skriptoteket_web() -> None:
    network = COMPOSE["networks"]["huleedu-dev-hule-network"]

    assert network == {"name": hemma_dev.HULEEDU_NETWORK, "external": True}
    assert SERVICES["web"]["networks"]["huleedu-dev-hule-network"]["aliases"] == [
        "skriptoteket-web"
    ]
    assert SERVICES["worker"]["networks"] == ["default"]
    assert SERVICES["db"]["networks"] == ["default"]


def test_web_and_worker_use_rootless_socket_and_share_artifact_storage() -> None:
    for name in ("web", "worker"):
        service = SERVICES[name]
        assert service["environment"]["DOCKER_HOST"] == f"unix://{ROOTLESS_SOCKET}"
        assert f"{ROOTLESS_SOCKET}:{ROOTLESS_SOCKET}:ro" in service["volumes"]
        assert "artifacts_data:/app/.artifacts" in service["volumes"]
        assert "vault_data:/var/lib/skriptoteket/vault" in service["volumes"]
        assert service["environment"]["ARTIFACTS_ROOT"] == "/app/.artifacts"
        assert service["environment"]["VAULT_ROOT"] == "/var/lib/skriptoteket/vault"
        assert "user" not in service


def test_runner_image_setting_matches_built_runner_image() -> None:
    runner_image = SERVICES["runner"]["image"]

    assert SERVICES["runner"]["profiles"] == ["build-only"]
    assert SERVICES["web"]["environment"]["RUNNER_IMAGE"] == runner_image
    assert SERVICES["worker"]["environment"]["RUNNER_IMAGE"] == runner_image
    assert SERVICES["worker"]["image"] == SERVICES["web"]["image"]


def test_web_trusts_only_the_huleedu_staging_public_key() -> None:
    environment = SERVICES["web"]["environment"]
    key_path = environment["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"]

    assert {
        "type": "bind",
        "source": str(hemma_dev.IDENTITY_PUBLIC_KEY_HOST_PATH),
        "target": key_path,
        "read_only": True,
    } in SERVICES["web"]["volumes"]
    assert environment["HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID"] == "gateway-identity-rs256-v1"
    assert environment["HULEEDU_INTERNAL_IDENTITY_ISSUER"] == "api_gateway_service"
    assert environment["HULEEDU_INTERNAL_IDENTITY_AUDIENCE"] == "skriptoteket"
    assert "HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY" not in environment
    assert "private" not in str(SERVICES["web"]["volumes"])


def test_proof_export_mount_matches_lifecycle_paths() -> None:
    export_dir = hemma_dev.PROOF_EXPORT_HOST_PATH.parent
    container_dir = str(Path(hemma_dev.PROOF_EXPORT_CONTAINER_PATH).parent)

    assert {
        "type": "bind",
        "source": str(export_dir),
        "target": container_dir,
        "read_only": True,
    } in SERVICES["web"]["volumes"]


def test_vite_unit_serves_loopback_5173_with_gateway_and_backend_lanes() -> None:
    unit_text = (ROOT / "systemd" / hemma_dev.VITE_UNIT).read_text(encoding="utf-8")
    environment = dict(
        line.removeprefix("Environment=").split("=", 1)
        for line in unit_text.splitlines()
        if line.startswith("Environment=")
    )

    assert environment["VITE_DEV_HOST"] == "127.0.0.1"
    assert environment["VITE_DEV_PORT"] == "5173"
    assert environment["VITE_DEV_PROXY_TARGET"] == "http://127.0.0.1:18080"
    assert environment["VITE_DEV_BACKEND_PROXY_TARGET"] == "http://127.0.0.1:18000"
    assert environment["VITE_DEV_PUBLIC_API_PROXY_TARGET"] == "http://127.0.0.1:18000"
    assert environment["VITE_HULEEDU_AUTH_ENTRY_URL"] == "http://127.0.0.1:15174/api/auth/login"
    assert "VITE_HULEEDU_PROTECTED_API_BASE_URL" not in environment
    assert "WorkingDirectory=/home/paunchygent/apps/skriptoteket-dev/frontend" in unit_text
