#!/usr/bin/env bash
# Canonical on-host deploy + share-preview readiness gate for Hemma.
# Run this from ~/apps/skriptoteket through `pdm run hemma-deploy-share-previews`.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/pr-0277-share-previews-cutover-${RUN_STAMP}"

require_clean_git_checkout() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "Refusing to deploy with local git changes in ${ROOT_DIR}." >&2
    exit 1
  fi
}

sync_checkout_to_origin_main() {
  local current_branch
  current_branch="$(git rev-parse --abbrev-ref HEAD)"

  if [[ "$current_branch" != "main" ]]; then
    echo "==> Switching deployment checkout from ${current_branch} to main"
    git checkout main
  fi

  echo "==> Fetching latest origin/main"
  git fetch origin main
  echo "==> Fast-forwarding local main to origin/main"
  git pull --ff-only origin main
  echo "==> Deploying commit $(git rev-parse HEAD)"
}

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

require_clean_git_checkout
sync_checkout_to_origin_main

set -a
# shellcheck disable=SC1091
source .env
set +a

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
"${COMPOSE[@]}" up -d --build web worker

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


with urllib.request.urlopen("http://localhost:8000/healthz", timeout=10) as response:
    payload = response.read().decode("utf-8")
print(json.dumps({"status": response.status, "body": payload}, ensure_ascii=False))
PY

echo "Share-preview deploy/readiness gate passed."
echo "Artifacts: ${ARTIFACT_DIR}"
