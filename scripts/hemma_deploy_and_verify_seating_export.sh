#!/usr/bin/env bash
# Canonical on-host deploy + seating-export readiness gate for Hemma.
# Run this from ~/apps/skriptoteket after pull.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE=(sudo docker compose -f compose.prod.yaml)
SIR_CONVERT_ROOT="${SIR_CONVERT_A_LOT_HEMMA_ROOT:-$HOME/apps/sir-convert-a-lot}"
SIR_CONVERT_HOST_LANE_URL="${SIR_CONVERT_A_LOT_HOST_LANE_URL:-http://127.0.0.1:28085}"
SEATING_EXPORT_SHARED_WEBHOOK_PATH="/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
RUN_STAMP="$(date +%Y%m%d-%H%M%S)"
CORRELATION_PREFIX="pr-0125-seat-export-${RUN_STAMP}"
ARTIFACT_DIR="${ROOT_DIR}/.artifacts/pr-0125-seat-export-cutover-${RUN_STAMP}"

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required env var: $key" >&2
    exit 1
  fi
}

probe_sir_convert() {
  curl -fsS "${SIR_CONVERT_HOST_LANE_URL}/readyz" >/dev/null
  curl -fsS \
    -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
    "${SIR_CONVERT_HOST_LANE_URL}/v2/push/webhooks/subscriptions" >/dev/null
}

inventory_subscriptions() {
  local target_file="$1"
  curl -fsS \
    -H "X-API-Key: ${SIR_CONVERT_A_LOT_V2_API_KEY}" \
    "${SIR_CONVERT_HOST_LANE_URL}/v2/push/webhooks/subscriptions" >"$target_file"
}

assert_canonical_inventory() {
  local inventory_file="$1"
  local expected_callback_url="${SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL%/}${SEATING_EXPORT_SHARED_WEBHOOK_PATH}"
  python3 - "$inventory_file" "$expected_callback_url" "$SEATING_EXPORT_SHARED_WEBHOOK_PATH" <<'PY'
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

inventory_path = Path(sys.argv[1])
expected_callback_url = sys.argv[2]
shared_path = sys.argv[3]

payload = json.loads(inventory_path.read_text())
subscriptions = payload.get("subscriptions")
if not isinstance(subscriptions, list):
    raise SystemExit(f"{inventory_path}: missing subscriptions list")

canonical = []
stale_shared = []
legacy = []
for item in subscriptions:
    if not isinstance(item, dict):
        continue
    callback_url = item.get("callback_url")
    subscription_id = item.get("subscription_id")
    if not isinstance(callback_url, str) or not isinstance(subscription_id, str):
        continue
    callback_path = urlparse(callback_url).path
    if callback_url == expected_callback_url:
        canonical.append(subscription_id)
        continue
    if callback_path == shared_path:
        stale_shared.append(subscription_id)
        continue
    if callback_path.startswith(f"{shared_path}/"):
        legacy.append(subscription_id)

if len(canonical) != 1 or stale_shared or legacy:
    raise SystemExit(
        "Non-canonical seating export webhook state remains: "
        f"canonical={canonical}, stale_shared={stale_shared}, legacy={legacy}"
    )
PY
}

recreate_sir_convert() {
  if [[ ! -d "$SIR_CONVERT_ROOT/.git" ]]; then
    echo "Sir Convert repo not found at ${SIR_CONVERT_ROOT}. Cannot recreate service." >&2
    exit 1
  fi
  (
    cd "$SIR_CONVERT_ROOT"
    pdm run dev-recreate sir_convert_a_lot_prod
  )
}

if [[ ! -f .env ]]; then
  echo "Missing .env in $ROOT_DIR." >&2
  exit 1
fi

set -a
source .env
set +a

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

require_env "SIR_CONVERT_A_LOT_V2_BASE_URL"
require_env "SIR_CONVERT_A_LOT_V2_API_KEY"
require_env "SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL"
require_env "BOOTSTRAP_SUPERUSER_EMAIL"
require_env "BOOTSTRAP_SUPERUSER_PASSWORD"
require_env "SKRIPTOTEKET_DB_PASSWORD"
require_env "SECRET_KEY"

mkdir -p "$ARTIFACT_DIR"
echo "==> Writing PR-0125 cutover artifacts to ${ARTIFACT_DIR}"

echo "==> Probing Sir Convert-a-Lot on ${SIR_CONVERT_HOST_LANE_URL}"
if ! probe_sir_convert; then
  echo "Sir Convert preflight failed; recreating sir_convert_a_lot_prod via the supported Hemma surface."
  recreate_sir_convert
  probe_sir_convert
fi

echo "==> Capturing pre-reconcile webhook inventory"
inventory_subscriptions "${ARTIFACT_DIR}/subscriptions-before-reconcile.json"

echo "==> Building runner image"
"${COMPOSE[@]}" --profile build-only build runner

echo "==> Deploying Skriptoteket web + worker"
"${COMPOSE[@]}" up -d --build

echo "==> Applying database migrations"
"${COMPOSE[@]}" exec -T -e PYTHONPATH=/app/src web pdm run db-upgrade

echo "==> Verifying production Sir Convert env wiring inside skriptoteket-web"
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_BASE_URL=' >/dev/null
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_API_KEY=' >/dev/null
sudo docker exec skriptoteket-web env | grep '^SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=' >/dev/null
echo "==> Verifying production Sir Convert env wiring inside skriptoteket-worker"
sudo docker exec skriptoteket-worker env | grep '^SIR_CONVERT_A_LOT_V2_BASE_URL=' >/dev/null
sudo docker exec skriptoteket-worker env | grep '^SIR_CONVERT_A_LOT_V2_API_KEY=' >/dev/null
sudo docker exec skriptoteket-worker env | grep '^SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=' >/dev/null

echo "==> Re-probing Sir Convert-a-Lot after Skriptoteket deploy"
probe_sir_convert

echo "==> Reconciling seating-export webhook state"
sudo docker exec \
  -e PYTHONPATH=/app/src \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli reconcile-seating-export-webhooks \
  --correlation-id "${CORRELATION_PREFIX}-reconcile" \
  | tee "${ARTIFACT_DIR}/reconcile-result.json"

echo "==> Capturing post-reconcile webhook inventory"
inventory_subscriptions "${ARTIFACT_DIR}/subscriptions-after-reconcile.json"

echo "==> Verifying canonical-only webhook state after reconciliation"
assert_canonical_inventory "${ARTIFACT_DIR}/subscriptions-after-reconcile.json"

echo "==> Running callback-capable seating export smoke"
sudo docker exec \
  -e PYTHONPATH=/app/src \
  -e BOOTSTRAP_SUPERUSER_EMAIL="${BOOTSTRAP_SUPERUSER_EMAIL}" \
  -e BOOTSTRAP_SUPERUSER_PASSWORD="${BOOTSTRAP_SUPERUSER_PASSWORD}" \
  skriptoteket-web \
  pdm run python -m skriptoteket.cli smoke-seating-export-readiness \
  --timeout-seconds 240 \
  --poll-interval-seconds 2 \
  --correlation-id "${CORRELATION_PREFIX}-smoke" \
  | tee "${ARTIFACT_DIR}/smoke-result.json"

echo "==> Capturing post-smoke webhook inventory"
inventory_subscriptions "${ARTIFACT_DIR}/subscriptions-after-smoke.json"

echo "==> Re-verifying canonical-only webhook state after smoke"
assert_canonical_inventory "${ARTIFACT_DIR}/subscriptions-after-smoke.json"

echo "Seating export deploy/readiness gate passed."
echo "Artifacts: ${ARTIFACT_DIR}"
