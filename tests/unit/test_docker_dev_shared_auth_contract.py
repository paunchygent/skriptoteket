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
HULEEDU_PUBLIC_KEY_VOLUME = (
    "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH:-"
    "../../huleedu/secrets/local-runtime/internal-identity/"
    "gateway-internal-identity-public-key.pem}:"
    "/run/huleedu/internal-identity/gateway-internal-identity-public-key.pem:ro"
)
HULEEDU_PROD_PUBLIC_KEY_DIR_VOLUME = (
    "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR:-"
    "/home/paunchygent/apps/huledu/secrets/hemma-runtime/internal-identity}:"
    "/run/huleedu/internal-identity:ro"
)
HULEEDU_CONTAINER_PUBLIC_KEY_PATH = (
    "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH:-"
    "/run/huleedu/internal-identity/gateway-internal-identity-public-key.pem}"
)


def _service_environment(compose_path: Path, service_name: str) -> dict[str, str]:
    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    raw_environment = payload["services"][service_name]["environment"]
    return dict(entry.split("=", 1) for entry in raw_environment)


def test_frontend_docker_dev_uses_local_huleedu_gateway_for_shared_auth() -> None:
    compose_payload = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    frontend_service = compose_payload["services"]["frontend"]
    web_service = compose_payload["services"]["web"]
    frontend_environment = _service_environment(ROOT / "compose.yaml", "frontend")
    web_environment = _service_environment(ROOT / "compose.yaml", "web")

    assert frontend_service["networks"] == {"default": None, "hule-network": None}
    assert web_service["networks"]["hule-network"]["aliases"] == ["skriptoteket-web"]
    assert HULEEDU_PUBLIC_KEY_VOLUME in web_service["volumes"]
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"]
        == "/run/huleedu/internal-identity/gateway-internal-identity-public-key.pem"
    )
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID"] == "gateway-identity-rs256-v1"
    )
    assert web_environment["HULEEDU_INTERNAL_IDENTITY_ISSUER"] == "api_gateway_service"
    assert web_environment["HULEEDU_INTERNAL_IDENTITY_AUDIENCE"] == "skriptoteket"
    assert web_environment["PUBLIC_APP_BASE_URL"] == "${PUBLIC_APP_BASE_URL:-http://localhost:5173}"
    assert web_environment["PLAYWRIGHT_BROWSERS_PATH"] == "/ms-playwright"
    assert web_environment["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] == ""
    assert frontend_environment["COREPACK_ENABLE_DOWNLOAD_PROMPT"] == "0"
    assert (
        frontend_environment["VITE_DEV_BACKEND_PROXY_TARGET"]
        == "${VITE_DEV_BACKEND_PROXY_TARGET:-http://skriptoteket_web:8000}"
    )
    assert (
        frontend_environment["VITE_DEV_PROXY_TARGET"]
        == "${VITE_DEV_PROXY_TARGET:-http://huleedu_api_gateway_service:8080}"
    )
    assert (
        frontend_environment["VITE_HULEEDU_AUTH_BASE_URL"]
        == "${VITE_HULEEDU_AUTH_BASE_URL:-http://localhost:8080}"
    )
    assert (
        frontend_environment["VITE_HULEEDU_AUTH_ENTRY_URL"]
        == "${VITE_HULEEDU_AUTH_ENTRY_URL:-http://localhost:8080/auth/login}"
    )


def test_docker_dev_worker_does_not_inherit_host_playwright_platform_override() -> None:
    worker_environment = _service_environment(ROOT / "compose.yaml", "worker")

    assert worker_environment["PLAYWRIGHT_BROWSERS_PATH"] == "/ms-playwright"
    assert worker_environment["PLAYWRIGHT_HOST_PLATFORM_OVERRIDE"] == ""


def test_vite_dev_proxy_keeps_public_api_off_huleedu_gateway() -> None:
    vite_config = (ROOT / "frontend/apps/skriptoteket/vite.config.ts").read_text(encoding="utf-8")

    assert "const devBackendProxyTarget = process.env.VITE_DEV_BACKEND_PROXY_TARGET" in vite_config
    assert (
        "const devPublicApiProxyTarget = process.env.VITE_DEV_PUBLIC_API_PROXY_TARGET"
        in vite_config
    )
    assert vite_config.index('"/api/v1/public"') < vite_config.index('"/api"')
    assert vite_config.index('"/share/classroom"') < vite_config.index('"^/static/(?!spa)"')
    assert "target: devPublicApiProxyTarget" in vite_config
    assert "target: devBackendProxyTarget" in vite_config


def test_production_compose_mounts_huleedu_gateway_public_key_for_protected_api() -> None:
    compose_payload = yaml.safe_load((ROOT / "compose.prod.yaml").read_text(encoding="utf-8"))
    web_service = compose_payload["services"]["web"]
    web_environment = web_service["environment"]

    assert HULEEDU_PROD_PUBLIC_KEY_DIR_VOLUME in web_service["volumes"]
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_PATH"]
        == HULEEDU_CONTAINER_PUBLIC_KEY_PATH
    )
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID"]
        == "${HULEEDU_INTERNAL_IDENTITY_SIGNING_KEY_ID:-gateway-identity-rs256-v1}"
    )
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_ISSUER"]
        == "${HULEEDU_INTERNAL_IDENTITY_ISSUER:-api_gateway_service}"
    )
    assert (
        web_environment["HULEEDU_INTERNAL_IDENTITY_AUDIENCE"]
        == "${HULEEDU_INTERNAL_IDENTITY_AUDIENCE:-skriptoteket}"
    )
