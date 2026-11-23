#!/usr/bin/env bash
# Canonical on-host deploy + share-preview readiness gate for Hemma.
# Start it only with `pdm run hemma-deploy-share-previews`: the launcher
# (scripts/hemma_deploy_start.sh) syncs the checkout to origin/main and opens
# this worker under the production secrets set.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
COMPOSE_SECRETS=(
  sudo --preserve-env="${AGENT_SECRETS_VARIABLES:-}"
  docker compose -f compose.prod.yaml -f compose.secrets.prod.yaml
)
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/pr-0277-share-previews-cutover-${RUN_STAMP}"

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

if [[ $# -gt 0 ]]; then
  echo "This worker takes no arguments; start it with pdm run hemma-deploy-share-previews." >&2
  exit 2
fi

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

# .env carries configuration only. One dotenv parser reads just the named,
# non-secret settings this worker uses; a value already in the environment wins.
config="$(pdm run python scripts/hemma_deploy_config.py .env \
  BOOTSTRAP_SUPERUSER_EMAIL \
  HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR)"
while IFS='=' read -r name value; do
  [[ -n "$name" ]] || continue
  if [[ -z "${!name:-}" ]]; then
    export "${name}=${value}"
  fi
done <<<"$config"

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

require_env "BOOTSTRAP_SUPERUSER_EMAIL"
require_env "BOOTSTRAP_SUPERUSER_PASSWORD"
require_env "SKRIPTOTEKET_DB_PASSWORD"
require_env "SECRET_KEY"

export HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR="${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR:-/home/paunchygent/apps/huledu/secrets/hemma-runtime/internal-identity}"
HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH="${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_DIR}/gateway-internal-identity-public-key.pem"
if [[ ! -r "${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH}" ]]; then
  echo "Missing readable HuleEdu internal identity public key: ${HULEEDU_INTERNAL_IDENTITY_PUBLIC_KEY_HOST_PATH}" >&2
  exit 1
fi

mkdir -p "$ARTIFACT_DIR"
echo "==> Writing PR-0277 share-preview artifacts to ${ARTIFACT_DIR}"

echo "==> Deploying Skriptoteket web + worker"
"${COMPOSE_SECRETS[@]}" up -d --build web worker

echo "==> Applying database migrations"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run db-upgrade

echo "==> Running classroom share preview backfill"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run backfill-classroom-share-previews --fail-fast \
  | tee "${ARTIFACT_DIR}/backfill-result.txt"

echo "==> Running Playwright PNG smoke inside web image"
sudo docker exec -i \
  -e PYTHONPATH=/app/src \
  skriptoteket-web \
  pdm run python - <<'PY' \
  | tee "${ARTIFACT_DIR}/playwright-png-smoke.txt"
from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(
        viewport={"width": 1200, "height": 630},
        device_scale_factor=1,
    )
    page.set_content(
        """
        <!doctype html>
        <html lang="sv">
          <body style="margin:0;width:1200px;height:630px;background:#f8fafc;">
            <main style="width:1200px;height:630px;display:grid;place-items:center;">
              <div style="font:700 48px sans-serif;color:#0f172a;">PR-0277 preview smoke</div>
            </main>
          </body>
        </html>
        """,
        wait_until="networkidle",
    )
    png = page.screenshot(type="png", full_page=False)
    browser.close()

if not png.startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("Playwright screenshot did not return PNG bytes.")
print(f"container-playwright-smoke: ok size=1200x630 bytes={len(png)}")
PY

echo "==> Checking web health inside production container"
"${COMPOSE[@]}" exec -T web pdm run python - <<'PY'
import json
import urllib.request


with urllib.request.urlopen(
    urllib.request.Request(
        # Production refuses loopback ALLOWED_HOSTS entries, so the readiness
        # gate names the public host while connecting over loopback.
        "http://127.0.0.1:8000/healthz",
        headers={"Host": "skriptoteket.hule.education"},
    ),
    timeout=10,
) as response:
    payload = response.read().decode("utf-8")
print(json.dumps({"status": response.status, "body": payload}, ensure_ascii=False))
PY

echo "Share-preview deploy/readiness gate passed."
echo "Artifacts: ${ARTIFACT_DIR}"
