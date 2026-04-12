"""Skriptoteket Docker dev shared-auth configuration contract.

Purpose:
    Keep the normal Docker dev frontend lane pointed at the local HuleEdu
    Gateway instead of the public production auth edge.

Relationships:
    - Protects the shared browser-session login handoff used by
      `frontend/apps/skriptoteket/src/api/sharedAuth.ts`.
    - Guards the `frontend` service in `compose.yaml`, which backs the normal
      Docker dev stack.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _service_environment(compose_path: Path, service_name: str) -> dict[str, str]:
    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    raw_environment = payload["services"][service_name]["environment"]
    return dict(entry.split("=", 1) for entry in raw_environment)


def test_frontend_docker_dev_uses_local_huleedu_gateway_for_shared_auth() -> None:
    compose_payload = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    frontend_service = compose_payload["services"]["frontend"]
    environment = _service_environment(ROOT / "compose.yaml", "frontend")

    assert frontend_service["networks"] == {"default": None, "hule-network": None}
    assert environment["COREPACK_ENABLE_DOWNLOAD_PROMPT"] == "0"
    assert (
        environment["VITE_DEV_PROXY_TARGET"]
        == "${VITE_DEV_PROXY_TARGET:-http://huleedu_api_gateway_service:8080}"
    )
    assert (
        environment["VITE_HULEEDU_AUTH_BASE_URL"]
        == "${VITE_HULEEDU_AUTH_BASE_URL:-http://localhost:8080}"
    )
    assert (
        environment["VITE_HULEEDU_AUTH_ENTRY_URL"]
        == "${VITE_HULEEDU_AUTH_ENTRY_URL:-http://localhost:8080/auth/login}"
    )
